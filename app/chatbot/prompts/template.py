def prompt_template():
    template = """
----------------------------------------
### Chat History:
Below is the previous chat history between you and the customer:
{formatted_history}
----------------------------------------
### Customer Information:
Below is the available information about the customer (if none, this section will be blank):
{formatted_user}
**Note:** Do not use the customer's personal information in your response unless the customer explicitly requests it.
----------------------------------------
### Customer Question:
This is the question the customer just entered (it may contain spelling or grammatical errors):
{question}
----------------------------------------
### Similar Questions:
Four similar questions are listed to help you answer more accurately:
{similar_question}
----------------------------------------
### Answer: 
"""

    return template
