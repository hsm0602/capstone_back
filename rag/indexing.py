from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from .embeddings import get_vectorstore

def index_pdfs(pdf_paths: list[str]):
    all_docs = []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )

    for path in pdf_paths:
        loader = PyPDFLoader(path)
        page_docs = loader.load()  # 페이지 단위 Document 리스트

        # 메타데이터 추가
        for d in page_docs:
            d.metadata["filename"] = path.split("/")[-1]
            d.metadata["title"] = d.metadata.get("title", d.metadata.get("filename"))
            d.metadata["source_type"] = "pdf"
            d.metadata["category"] = "exercise_guide"  # 필요시 수정
            # d.metadata["exercise_id"] = ... ← 이런 식으로 특정 운동 문서로도 묶을 수 있음

        chunk_docs = text_splitter.split_documents(page_docs) # chunk 단위 Document 리스트

        all_docs.extend(chunk_docs)

    # 벡터 DB에 저장
    vs = get_vectorstore()
    vs.add_documents(all_docs)
    vs.persist()

    print(f"총 {len(all_docs)}개의 문서를 벡터 DB에 저장했습니다.")

if __name__ == "__main__":
    index_pdfs(["docs/home_training_guide.pdf", "docs/exercise_difficulty_and_substitution.pdf", "docs/program_design_principles.pdf", "docs/body_condition_exercise_modification_guide.pdf", "docs/exercise_physiology_guide.pdf"])