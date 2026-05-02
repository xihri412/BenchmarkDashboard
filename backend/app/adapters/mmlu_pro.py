from app.adapters.common_choice import ExactMatchChoiceAdapter


class MmluProAdapter(ExactMatchChoiceAdapter):
    def __init__(self) -> None:
        super().__init__("MMLU-Pro")
