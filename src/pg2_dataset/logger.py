import logging


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s: %(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )

    return logger
