import logging
import os
from typing import Union
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
