from threading import Event, Thread
import time

from six.moves.queue import Queue, Empty


class CachePipeline(object):
    def __init__(self, spider, cache):
        self.spider = spider
        self.cache = cache
        self.queue_size = 100
        self.input_queue = Queue()
        self.result_queue = Queue()
        self.is_working = Event()
        self.is_paused = Event()

        self.thread = Thread(target=self.thread_worker)
        self.thread.daemon = True
        self.thread.start()

    def has_free_resources(self):
        return (self.input_queue.qsize() < self.queue_size
                and self.result_queue.qsize() < self.queue_size)

    def is_idle(self):
        return (not self.is_working.is_set()
                and not self.input_queue.qsize()
                and not self.input_queue.qsize())

    def thread_worker(self):
        while True:
            while self.is_paused.is_set():
                time.sleep(0.01)
            try:
                action, data = self.input_queue.get(True, 0.1)
            except Empty:
                if self.spider.shutdown_event.is_set():
                    #print('!CACHE: EXITING CACHE PIPELINE')
                    return self.shutdown()
                #else:
                #    print('no shutdown event')
            else:
                self.is_working.set()
                #print('!CACHE:got new task from input: %s:%s'
                #      % (action, data))
                assert action in ('load', 'save', 'pause')
                if action == 'load':
                    task, grab = data
                    result = None
                    if self.is_cache_loading_allowed(task, grab):
                        #print('!CACHE: query cache storage')
                        result = self.load_from_cache(task, grab)
                    if result:
                        #print('!CACHE: cached result is None')
                        #print('!! PUT RESULT INTO CACHE PIPE '
                        #      'RESULT QUEUE (cache)')
                        self.result_queue.put(('network_result', result))
                    else:
                        self.result_queue.put(('task', task))
                elif action == 'save':
                    task, grab = data
                    if self.is_cache_saving_allowed(task, grab):
                        with self.spider.timer.log_time('cache'):
                            with self.spider.timer.log_time('cache.write'):
                                self.cache.save_response(task.url, grab)
                elif action == 'pause':
                    self.is_paused.set()
                self.is_working.clear()

    def is_cache_loading_allowed(self, task, grab):
        # 1) cache data should be refreshed
        # 2) cache is disabled for that task
        # 3) request type is not cacheable
        return (not task.get('refresh_cache', False)
                and not task.get('disable_cache', False)
                and grab.detect_request_method() == 'GET')

    def is_cache_saving_allowed(self, task, grab):
        """
        Check if network transport result could
        be saved to cache layer.

        res: {ok, grab, grab_config_backup, task, emsg}
        """

        if grab.request_method == 'GET':
            if not task.get('disable_cache'):
                if self.spider.is_valid_network_response_code(grab.doc.code,
                                                              task):
                    return True
        return False

    def load_from_cache(self, task, grab):
        with self.spider.timer.log_time('cache'):
            with self.spider.timer.log_time('cache.read'):
                cache_item = self.cache.get_item(
                    grab.config['url'], timeout=task.cache_timeout)
                if cache_item is None:
                    return None
                else:
                    with self.spider.timer.log_time(
                        'cache.read.prepare_request'
                    ):
                        grab.prepare_request()
                    with self.spider.timer.log_time(
                        'cache.read.load_response'
                    ):
                        self.cache.load_response(grab, cache_item)
                    grab.log_request('CACHED')
                    self.spider.stat.inc('spider:request-cache')

                    return {'ok': True, 'task': task, 'grab': grab,
                            'grab_config_backup': grab.dump_config(),
                            'emsg': None}

    def shutdown(self):
        try:
            self.cache.close()
        except AttributeError:
            print('Cache %s does not support close method' % self.cache)

    def pause(self):
        self.add_task(('pause', None))
        self.is_paused.wait()

    def resume(self):
        self.is_paused.clear()

    def get_ready_results(self):
        res = []
        while True:
            try:
                action, result = self.result_queue.get_nowait()
            except Empty:
                break
            else:
                assert action in ('network_result', 'task')
                res.append((action, result))
        return res

    def add_task(self, task):
        self.input_queue.put(task)
        #print('!CACHE: Added new task')
