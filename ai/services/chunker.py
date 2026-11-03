from langchain_text_splitters import RecursiveCharacterTextSplitter

_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


def split(text: str) -> list[str]:
    return _splitter.split_text(text)
