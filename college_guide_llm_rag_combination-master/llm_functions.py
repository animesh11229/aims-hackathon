import ast
import pprint
from datetime import datetime

import holiday_lister

import file_management_base
import email_body_extractor
import google.generativeai as gen
from google import genai
from google.genai import types
from dotenv import load_dotenv
import json
import os
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import re
import logging

logger,service,apikey,client=None,None,None,None

with open("static/holidays.txt", "w", encoding="utf-8") as f:
    print(holiday_lister.get_holiday_list(), file=f)


def initialize():
    global logger,service,apikey,client
    logger = logging.getLogger(__name__)
    service = file_management_base.authenticate_and_return_service()

    load_dotenv(override=True)
    apiKey = os.getenv('GEMINI_API_KEY')
    # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    client = genai.Client(api_key=apiKey)
    gen.configure(api_key=apiKey)


def parse_list_string(s):
    s = s.strip()

    # Replace only first and last char if they're not normal quotes
    if s and s[0] not in ['[',']']:
        s = s[1:]
    if s and s[-1] not in ['[',']']:
        s = s[:-1]
    return s
def safe_extract_assistant_text(response):
    # Try multiple places where assistant text might live
    try:
        # genai responses: response.candidates[0].content[0].text
        cand = response.candidates[0]
        # try various shapes:
        if hasattr(cand, "content"):
            cont = cand.content
            # cont can be list or object with parts
            if isinstance(cont, list) and len(cont) > 0 and hasattr(cont[0], "text"):
                return cont[0].text
            if hasattr(cont, "text"):
                return cont.text
            if hasattr(cont, "parts"):
                for p in cont.parts:
                    if isinstance(p, dict) and p.get("text"):
                        return p["text"]
        # fallback to str(response)
        return str(response)
    except Exception:
        return None

def initialize_gemini_model(chat_history=[]):
    system_prompt = ""
    with open("static/system_prompt_main_llm.txt", "r", encoding="utf-8") as prompt:
        system_prompt = prompt.read()

    model = gen.GenerativeModel(
        model_name='gemini-2.5-flash',
        tools=list(tool_registry.values()),
        system_instruction=system_prompt,# Pass the function objects themselves
        safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
    )

    return model.start_chat(history=chat_history)

# this is a tool for llm
#Write the most current hierarchy structure
def reload_hierarchy():
    """
    updates the hierarchy.txt file to map the latest updates of actual google drive
    use this function to pull out latest updates from database
    :return True if succesfully executed , False if fails:
    """
    with open("static/paths.txt", "w", encoding="utf-8") as f:
        file_management_base.list_files_with_full_path(service, file_management_base.TARGET_FOLDER_ID,f=f)
    with open("static/hierarchy.txt", "w", encoding="utf-8") as f:
        file_management_base.list_items_recursively(service,file_management_base.TARGET_FOLDER_ID,f=f)
    return True

def request_hierarchy_contents():
    '''
    only and only use this function if user specifically use $$DEBUG$$ tag at staring and requesting to view or show hierarchy contents
    :return: hierarchy raw text data
    '''
    with open("static/hierarchy.txt", "r", encoding="utf-8") as f:
        return f.read()

# this is a tool for llm
def request_files_for_context(query:str):
    '''
    Retrieves raw file content for contextual understanding.
    This tool is used to fetch the actual text content of files
    from a knowledge base. The output is intended for the LLM to
    read and synthesize a comprehensive response, not to be shown
    directly to the user.

    The function is designed to be highly reliable and should be used
    when the user's query requires specific, factual information that is
    likely to be contained within a document, such as a syllabus,
    campus information about navigation or buildings or classrooms, timetable , faculties


    Args:
    query (list): list of paths of the file that seems to contain relevant information from hierarchy

    Returns:
    list[str]: A list of strings, where each string is the raw
    text content of a relevant file. Returns an empty
    list if no matching files are found.


    examples:
    For "whats the schedule of wednesday"
    query : ['NSUT/$$SYSTEM$$:timetable_lectureHalls_faculties.json']

    2. For "where is room 6320"
    query : ['NSUT/about_clg/$$SYSTEM$$Comprehensive Campus and navigation Guide NSUT.pdf']

    '''

    print(f"query is : {list(query)}")


    file_paths=list(query)

    return [
        file_management_base.get_upload_ready_file_for_llm(file_management_base.get_file_name_from_id(service,fileid),file_management_base.download_file_content(service,fileid))
        for fileid in [file_management_base.get_file_id_from_path(service,path) for path in file_paths]
    ]


# this is a tool for llm
def request_files_id_2sharable_link_gemini_rag(query:dict):
    """
    Provides direct, sharable download links for files requested by the user.

    Call this function ONLY when the user explicitly requests a downloadable file,
    such as notes, documents, or syllabi. It is triggered by phrases like:
        - "Send me the presentation slides."
        - "Do you have the notes from yesterday's lecture?"
        - "I need the syllabus for Chemistry 202."
        - "Can I get the link to the shared drive?"

    **!! CRITICAL INSTRUCTION: NEVER MODIFY THE DOWNLOAD LINKS !!**
    - The URLs provided by this tool are unique and pre-signed. **ANY** modification,
      including shortening, encoding, or altering even a single character, will
      permanently invalidate the link and make the file inaccessible.
    - You **MUST** present the links to the user exactly, character-for-character,
      as they are returned by this function.
    - You may format your response to make the link clickable (e.g., using Markdown),
      but the underlying URL string itself must remain completely unaltered.

      - **Correct Example:** `[Maths Lecture Notes](https://example.com/file?id=123&signature=abc)`
      - **Incorrect Example:** `[Maths Lecture Notes](https://example.com/file?id=123)` (This is WRONG because the signature was removed).

    **Additional Guidelines:**
    - The links returned by this function are for the **USER**, not for the LLM.
    - Present these links directly to the user in your response.
    - This tool does NOT provide context for generating answers; it only provides links.

    Args:
        query (dict): A structured query to identify the requested files.
            The dictionary should contain specific keys to filter the file
            database. Any key not relevant to the user's request
            should be set to `None`. The format is:
            {
                "tag": "The file type, e.g., '$$SYSTEM$$', '$$USER-NOTES$$', '$$USER-BOOK$$'",
                "subject": "The main subject,try to write exact subject as given in hierarchy folder names e.g., 'maths', 'cad'",
                "by_user": "The name of the user who created the notes,DO NOT EDIT THIS VALUE COPY IT AS IT IS FROM user prompt in lowercase e.g., 'deshna'",
                "lecture_no": "The specific lecture number, e.g., 3",
                "date": "A specific date or date range !! in format as YYYY-MM-DD only, e.g., '2025-08-12',for range '2025-08-(04-22)'",
                "context": "A specific topic within a subject, e.g., 'hyperbolic functions'",
                "semester": "The semester number, e.g., 1"
            }

    Returns:
        tuple[list[str], list[str]]: A tuple containing two lists:
        1. A list of sharable, **unalterable** URL strings for the requested files.
        2. A list of the corresponding file paths for the LLM's context.
        Returns an empty tuple ([], []) if no files are found.

    Examples:
        User Request: "give me notes of maths sem 1 lecture 3 on hyperbolic functions"
        Query:
        {
            "tag": "$$USER-NOTES$$",
            "subject": "maths",
            "by_user": None,
            "lecture_no": 3,
            "date": None,
            "context": "hyperbolic functions",
            "semester": 1
        }

        User Request: "all notes of cad"
        Query:
        {
            "tag": "$$USER-NOTES$$",
            "subject": "cad",
            "by_user": None,
            "lecture_no": None,
            "date": None,
            "context": None,
            "semester": None
        }

        User Request: "notes of cad from date 2025-08-04 to 2025-08-25"
        Query:
        {
            "tag": "$$USER-NOTES$$",
            "subject": "cad",
            "by_user": None,
            "lecture_no": None,
            "date": "2025-08-(04-25)",
            "context": None,
            "semester": None
        }

        User Request: "notes of maths by deshna"
        Query:
        {
            "tag": "$$USER-NOTES$$",
            "subject": "maths",
            "by_user": "deshna",
            "lecture_no": None,
            "date": None,
            "context": None,
            "semester": None
        }

        User Request: "give me book of maths about hyperbolic functions"
        Query:
        {
            "tag": "$$USER-BOOK$$",
            "subject": "maths",
            "by_user": None,
            "lecture_no": None,
            "date": None,
            "context": "hyperbolic functions",
            "semester": None
        }

        User Request: "give me a book on hyperbolic functions"
        Query:
        {
            "tag": "$$USER-BOOK$$",
            "subject": None,
            "by_user": None,
            "lecture_no": None,
            "date": None,
            "context": "hyperbolic functions",
            "semester": None
        }

        User Request: "give me the syllabus of cad"
        Query:
        {
            "tag": "$$SYSTEM$$",
            "subject": "cad",
            "by_user": None,
            "lecture_no": None,
            "date": None,
            "context": "syllabus",
            "semester": None
        }
    """
    # file paths from gemini raw
    file_paths = match_percent_rag(dict(query))
    #print(file_paths)
    #checking if the link was generated prior to this request
    with open("static/links.txt","r",encoding="utf-8") as f:
        already_gen_links = { ast.literal_eval(i.replace('\n',''))[0]:ast.literal_eval(i.replace('\n',''))[1] for i in f.readlines()}


    # filtering which are the new files user requested that we don't have a link of
    file_to_find_id = [path for path in file_paths if path not in already_gen_links]



    #print(file_to_find_id)
    #id's of new files requested
    ids = [file_management_base.get_file_id_from_path(service, path) for path in file_to_find_id]
    links = [file_management_base.create_sharable_link(service,id) for id in ids]
    #updating our links file
    with open("static/links.txt","a+",encoding="utf-8") as f:
        for link in zip(file_paths, links):
            if link not in already_gen_links.items():
                if link[1] != None:
                    print(link,file=f)
    # returning final result as all the links+file paths for context
    return (links+[already_gen_links.get(file) for file in file_paths if file in already_gen_links],file_paths)





# gemini response core block
def _extract_candidates(response):
    """Return a list-like of candidates or None."""
    try:
        if hasattr(response, "result") and hasattr(response.result, "candidates"):
            return response.result.candidates
        if hasattr(response, "candidates"):
            return response.candidates
        if isinstance(response, dict) and "candidates" in response:
            return response["candidates"]
    except Exception:
        logger.debug("Could not read candidates from response", exc_info=True)
    return None

def _extract_text_from_candidate(c):
    """Try multiple shapes to extract assistant text from a candidate."""
    try:
        # protobuf-like: content.parts[0].text
        if hasattr(c, "content"):
            cont = c.content
            if hasattr(cont, "parts") and cont.parts:
                part = cont.parts[0]
                if isinstance(part, dict):
                    return part.get("text")
                elif hasattr(part, "text"):
                    return part.text
            if hasattr(cont, "text"):
                return cont.text
            if isinstance(cont, list) and len(cont) > 0:
                first = cont[0]
                if isinstance(first, dict):
                    return first.get("text")
                elif hasattr(first, "text"):
                    return first.text
        # dict-like candidate:
        if isinstance(c, dict):
            cont = c.get("content")
            if isinstance(cont, dict):
                parts = cont.get("parts")
                if parts and isinstance(parts, list) and len(parts) > 0:
                    p = parts[0]
                    if isinstance(p, dict):
                        return p.get("text")
                return cont.get("text")
    except Exception:
        logger.debug("Failed to extract text from candidate", exc_info=True)
    return None

def _extract_function_call_from_candidate(c):
    """Try multiple shapes to extract function_call (dict or object)."""
    try:
        # candidate.content.parts[0].function_call
        if hasattr(c, "content"):
            cont = c.content
            if hasattr(cont, "parts") and cont.parts:
                part = cont.parts[0]
                if isinstance(part, dict) and "function_call" in part:
                    return part.get("function_call")
                elif hasattr(part, "function_call"):
                    return part.function_call
            if isinstance(cont, list) and len(cont) > 0:
                first = cont[0]
                if isinstance(first, dict) and "function_call" in first:
                    return first["function_call"]
                elif hasattr(first, "function_call"):
                    return first.function_call
        # sometimes candidate itself has function_call
        if hasattr(c, "function_call"):
            return c.function_call
        if isinstance(c, dict) and "function_call" in c:
            return c["function_call"]
    except Exception:
        logger.debug("Failed to extract function_call", exc_info=True)
    return None

def _parse_arguments(raw_args):
    """Turn raw_args into a dict in a tolerant way."""
    if not raw_args:
        return {}
    # already a dict-like
    if isinstance(raw_args, dict):
        return raw_args
    # string -> try json
    if isinstance(raw_args, str):
        try:
            return json.loads(raw_args)
        except Exception:
            # try simple normalization (single quotes -> double quotes)
            try:
                return json.loads(raw_args.replace("'", '"'))
            except Exception:
                # Try to extract a {...} substring and parse
                m = re.search(r"(\{.*\})", raw_args, flags=re.S)
                if m:
                    try:
                        return json.loads(m.group(1).replace("'", '"'))
                    except Exception:
                        pass
        # as last resort, return an empty dict so we can still call the tool without args
        return {}
    # list/tuple of pairs or object convertible to dict
    try:
        return dict(raw_args)
    except Exception:
        return {}

def gemini_main_response(user_prompt: str, gemini_chat):
    """
    Sends the user prompt to gemini_chat, handles an optional function_call,
    executes the selected function (if valid) with selected_function(**dict(args)),
    sends the function result back to the model as a tool-like message,
    and finally returns the model's final assistant text (string).
    """
    # 1) initial model call
    now = datetime.now()
    current_datetime_info = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "day": now.strftime("%A")
    }
    with open("static/holidays.txt","r",encoding="utf-8") as f:
        holidays = f.read()
    response = gemini_chat.send_message([user_prompt,request_hierarchy_contents(),json.dumps(current_datetime_info),holidays])

    # 2) extract candidates and primary candidate
    candidates = _extract_candidates(response)
    if not candidates or len(candidates) == 0:
        # Nothing parsed: return a readable fallback
        return str(response)

    cand0 = candidates[0]

    # 3) extract assistant text (may be used as fallback)
    assistant_text = _extract_text_from_candidate(cand0)

    # 4) extract possible function_call
    function_call = _extract_function_call_from_candidate(cand0)

    # 5) if model returned a function_call, validate and attempt to run it
    if function_call:
        # normalize name and args
        if isinstance(function_call, dict):
            fname = function_call.get("name")
            raw_args = function_call.get("arguments")
        else:
            fname = getattr(function_call, "name", None)
            raw_args = getattr(function_call, "arguments", None)

        # guard: empty or whitespace-only name -> treat as NO_TOOL
        if not (isinstance(fname, str) and fname.strip()):
            logger.info("Model returned empty/whitespace function name -> falling back to assistant text.")
            return assistant_text or "I couldn't parse the model's response; please rephrase."

        # ensure the tool exists
        if fname not in tool_registry:
            logger.info("Model requested unknown function '%s' -> falling back to assistant text.", fname)
            return assistant_text or f"Model requested unknown function: {fname}"

        # parse args as a dict (we keep the behavior you requested)
        args_dict = dict(function_call.args)
        print(f'calling function {fname} with arguments {args_dict}')

        # Call the selected function using **dict(args) pattern the project expects.
        try:
            selected_function = tool_registry[fname]
            # ensure we pass a plain dict to satisfy selected_function(**dict(args))
            # This will raise a TypeError if selected_function doesn't accept kwargs — let it propagate to be handled below.
            tool_result = selected_function(**args_dict)
        except TypeError as te:
            logger.exception("TypeError while calling tool %s with args %r", fname, args_dict)
            return f"Error: tool '{fname}' could not be called with provided arguments: {te}"
        except Exception as e:
            logger.exception("Exception while running tool %s", fname)
            return f"Error running tool {fname}: {e}"

        # --- SEND THE RESULT BACK TO THE MODEL ---
        # Use the exact structure you provided so the model can consume it as tool output.
        func_resp_content = {
            "role": "tool",
            "parts": [
                {
                    "function_response": {
                        "name": fname,
                        "response": {"tool_result": tool_result}
                    }
                }
            ]
        }

        # send the tool response back to the model; the model will generate the final text reply
        # (wrap in list for consistency with how you call send_message)
        final_response = gemini_chat.send_message(func_resp_content)

        # parse final_response and return final assistant text
        final_cands = _extract_candidates(final_response)
        if final_cands and len(final_cands) > 0:
            final_text = _extract_text_from_candidate(final_cands[0])
            return final_text or str(final_response)
        else:
            return str(final_response)

    # 6) no function_call -> return assistant_text (final answer)
    return assistant_text or str(response)
#block ends



def tool_reload_announcements():
    """
    reloads the announcements file , pulls out the latest announcements from database
    :return:
    """
    with open("static/announcements.txt", "w", encoding="utf-8") as f:
        for email in email_body_extractor.read_emails_with_subject_alternative():
            print(f"{email}",file=f)


# this is a llm tool
def read_announcements(howMany:int)->list:
    how_many = int(howMany)
    '''
    a list of the latest announcements, always sort them from first newest to oldest last
    . by default keep param howMany at 5 unless the user specifies how many announcements to return , !!! never return the result as it is , read the contents and respond in your own words
    :param howMany: this defines the number of announcements to return from the database 
    :return: list of announcements
    '''

    tool_reload_announcements()
    announcements = ""
    with open("static/announcements.txt", "r", encoding="utf-8") as f:
        announcements = f.readlines()
    while "\n"in announcements:
        announcements.remove("\n")
    return list(reversed(announcements))[:how_many]


tool_registry = {
    "request_files_id_2sharable_link_gemini_rag": request_files_id_2sharable_link_gemini_rag,
    "reload_hierarchy": reload_hierarchy,
    "read_announcements":read_announcements,
    "request_files_for_context":request_files_for_context,
}






























def match_percent_rag(query):

    pprint.pprint(dict(query))

    with open("static/paths.txt", "r", encoding="utf-8") as f:
        paths = f.readlines()


    for path in paths.copy():
        #filtering based on tag
        tag =query['tag']
        if tag !=None:
            if tag not in path:
                #print("this path does now match the tag :",path)
                paths.remove(path)



    for path in paths.copy():
        #filtering based on tag
        sem = query['semester']
        if sem != None:
            if f'semester-{int(sem)}' not in path:
                #print("this path does now match the semester :",path)
                paths.remove(path)




    for path in paths.copy():
        #filtering based on tag
        sub = query['subject']
        if sub != None:
            if sub not in path:
                #print("this path does now match the subject :",path)
                paths.remove(path)


    for path in paths.copy():
        #filtering based on tag
        user  = query['by_user']
        if user != None:
            if user not in path:
                #print("this path does now match the by_user :",path)
                paths.remove(path)

    for path in paths.copy():
        lecture = query['lecture_no']
        if lecture != None:
            if f"lecture-{int(lecture)}" not in path:
                #print("this path does now match the by_user :", path)
                paths.remove(path)

    for path in paths.copy():
        # filtering based on tag
        date = query['date']
        if date != None:
            if date not in path:
                #print("this path does now match the date :", date)
                paths.remove(path)

    paths_new = [path.replace("\n","") for path in paths]

    return paths_new




if __name__ == "__main__":
    initialize()
    print(file_management_base.create_sharable_link(service,"11RsiFxGMy2Gx2I4FDo6ra2l4g9IyxAeD"))
    #reload_hierarchy()
    #read_announcements(1)
    #match_percent_rag(None)
    #print(request_files_id_2sharable_link_gemini_rag("$$REQUEST-FILE$$ give me all notes of maths sem 1"))


'''debug testing here '''
# reload_hierarchy()
# gemini_chat = initialize_gemini_model()
# user_prompt = "what are washrooms?"
# print(gemini_main_response(user_prompt, gemini_chat))
# tool_reload_announcements()
# print(tool_read_announcements())
#gemini_rag_id_2file("what is the syllabus of maths semister 1")

