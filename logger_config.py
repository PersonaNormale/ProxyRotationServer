import logging


def setup_logging(log_file=None, log_level=logging.INFO):
    logger = logging.getLogger("ProxyServer")
    logger.setLevel(log_level)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    handler = logging.FileHandler(
        log_file) if log_file else logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


logger = setup_logging()
