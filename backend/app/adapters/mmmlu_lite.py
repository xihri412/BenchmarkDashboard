from app.adapters.common_choice import ExactMatchChoiceAdapter


class MmmluLiteAdapter(ExactMatchChoiceAdapter):
    def __init__(self) -> None:
        super().__init__("MMMLU-lite")
