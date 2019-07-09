import abc
from typing import List, Dict, Optional, Any


class Task(abc.ABC):
    def pre_call(self, *args, **kwargs) -> (List, Dict, Any):
        return args, kwargs, None

    @abc.abstractmethod
    def call(self, *args, **kwargs) -> Optional[Any]:
        pass

    def post_call(self, output, *args, **kwargs) -> Any:
        return output

    def __call__(self, *args, **kwargs):
        # short circuit if pre_call returns an output
        args, kwargs, output = self.pre_call(*args, **kwargs)
        if output is not None:
            return output

        output = self.call(*args, **kwargs)
        return self.post_call(output, *args, **kwargs)


def load_cache():
    """Get a database connection"""
    return {}


class CachedTask(Task):
    def __init__(self):
        self._cache = load_cache()

    def _get_task_name(self):
        return self.__class__.__name__

    def _get_cache_key(self, *args, **kwargs):
        return self._get_task_name(), args, kwargs

    def pre_call(self, *args, **kwargs) -> (List, Dict, Any):
        key = self._get_cache_key()
        if key in self._cache:
            return args, kwargs, self._cache[key]
        else:
            return args, kwargs, None

    @abc.abstractmethod
    def call(self, *args, **kwargs) -> Optional[Any]:
        pass

    def post_call(self, output, *args, **kwargs) -> Any:
        self._cache[self._get_cache_key(*args, **kwargs)] = output
        return output


for output in outputs:
    serialized_output = serializer.serialize(output)
    save(serialized_output)


# def preprocess_data(x_raw, y_raw):
#     pass
#
#
# class PreprocessTask(CachedTask):
#     def call(self, x_raw, y_raw):
#         pass
#
#
# class Struct:
#     pass
#
#
# cluster = Struct()
# x, y = PreprocessTask(location=cluster.big_machine)(x_raw, y_raw)