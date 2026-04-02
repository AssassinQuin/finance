from .fund_presenter import ForexPresenter, FundPresenter
from .gold_presenter import GoldPresenter
from .quote_presenter import QuotePresenter


class ConsolePresenter(QuotePresenter, GoldPresenter, FundPresenter, ForexPresenter):
    pass
