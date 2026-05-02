from app.adapters.common_choice import ExactMatchChoiceAdapter


class MmluReduxAdapter(ExactMatchChoiceAdapter):
    def __init__(self) -> None:
        super().__init__("MMLU-Redux")
