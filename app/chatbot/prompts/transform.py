def transform_prompt() -> str:
    template = """
    You are a helpful assistant whose task is to generate multiple search queries based on a given input query (the input may be unclear, contain spelling mistakes, or typing errors).
    Generate {num_queries} clear and easy-to-understand search queries (correcting errors and clarifying the meaning), with each query on a new line, and all queries must be related in meaning to the original input query. Most of questions are about tourism, travel, and culture in Vietnam.
    Pay close attention to the last part of the sentence — it is important. The first two queries should be Vietnamese, and the last two should be English.
    Query: {query}
    Queries:
    """
    return template