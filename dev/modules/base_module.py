import logging


class BaseModule:
    m_Inited = False

    @classmethod
    def m_init(cls):
        cls.m_Inited = True
        logging.info(f'[{cls.__name__}] init')
