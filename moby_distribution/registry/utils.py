import logging
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, ContextManager, Iterator, Union

import libtrust
from libtrust.keys import ec_key, rs_key

logger = logging.getLogger(__name__)


def get_private_key() -> Union[libtrust.ECPrivateKey, libtrust.RSAPrivateKey]:
    key = os.getenv("MOBY_DISTRIBUTION_PRIVATE_KEY")
    password = os.getenv("MOBY_DISTRIBUTION_PRIVATE_KEY_PASSWORD")
    if key is not None:
        try:
            return ec_key.ECPrivateKey.from_pem(key, password)
        except Exception:
            try:
                return rs_key.RSAPrivateKey.from_pem(key, password)
            except Exception:
                logger.warning("Unknown private key.")
    return ec_key.generate_private_key()


def validate_media_type(cls, media_type: str) -> str:
    if hasattr(cls, "content_type") and cls.content_type() != media_type:
        raise ValueError("unknown media type '{}'".format(media_type))

    if hasattr(cls, "content_types") and media_type not in cls.content_types():
        raise ValueError("unknown media type '{}'".format(media_type))

    return media_type


def new_method_proxy(func):
    def inner(self, *args):
        if "_wrapped" not in self.__dict__:
            self.__dict__["_wrapped"] = self.__dict__["_factory"]()
        return func(self._wrapped, *args)

    return inner


class LazyProxy:
    def __init__(self, obj: Callable[..., Any]):
        self.__dict__["_factory"] = obj

    __getattr__ = new_method_proxy(getattr)
    __setattr__ = new_method_proxy(setattr)
    __dir__ = new_method_proxy(dir)

    def __repr__(self):
        return repr(self.__dict__["_wrapped"])


def __generate_temp_dir__(suffix=None) -> Iterator[Path]:
    path = None
    try:
        path = Path(tempfile.mkdtemp(suffix=suffix))
        logger.debug('Generating temp path: %s', path)
        yield path
    finally:
        if path and path.exists():
            shutil.rmtree(path)


generate_temp_dir: Callable[..., ContextManager[Path]] = contextmanager(__generate_temp_dir__)
