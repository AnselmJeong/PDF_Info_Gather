from agent import config, clients
from db import execute_query, set_db_name
import json


aggregate_prompt = config["aggregate_prompt"]
model_name = config["openai_model_name"]
openai = clients["openai"]


def process_LLM_output(answer: str) -> list[dict]:
    """
    Convert the output from LLM to a list of dictionaries with theme and item_indices.
    Args:
        answer (str): The output from LLM in string format.
        OpenAI returns an already parsed dict or list, while other LLMs may return a string.
    Returns:
        list[dict]: A list of dictionaries.
    """
    if isinstance(answer, dict) or isinstance(answer, list):
        answers = answer
    else:
        answers = json.loads(answer)

    if "themes" not in answers:
        raise ValueError("No 'themes' key found in the answer")

    for theme in answers["themes"]:
        # For each item in the theme, extract index and content
        indices = []
        contents = []
        for item in theme.get("items", []):
            # Split on first period and strip whitespace
            index, content = item.split(".", 1)
            indices.append(int(index))
            contents.append(content.strip())

        # Add new fields to the theme dictionary
        theme["item_indices"] = indices

    return answers


def get_found_themes(answers: dict) -> list[str]:
    try:
        return [theme["theme"] for theme in answers["themes"]]
    except KeyError as e:
        print(f"Error getting keys from answers: {e}")
        return []


def find_item_indices(target_value: str, answers: dict):
    """
    Filters item indices from the answers dictionary where the theme key matches the target value.

    Parameters:
    target_value (str): The value to match against the theme key.
    answers (dict): The dictionary containing themes.

    Returns:
    list: A list of item indices that match the target value.
    """
    try:
        return [
            theme.get("item_indices", [])
            for theme in answers.get("themes", [])
            if theme.get("theme") == target_value
        ][0]
    except IndexError:
        return []


def get_theme_items_from_db(search_theme, answers):
    """
    Get the items from the database that match the query (=theme).
    Args:
        query (str): The theme you want to find the items that belong to.
        answers (list[dict]): The list of dictionaries obtained from the LLM output by `process_LLM_output()`.
    Returns:
        dict: A dictionary with the theme as the key and the items as the values.
    """
    idx = find_item_indices(search_theme, answers)
    if idx == []:
        return []

    # Modified query to include citations using LEFT JOIN
    query = f"""
        SELECT i.id, i.source_file, i.theme, i.snippet, i.supports, i.rejects,
               c.citation
        FROM knowledge_snippets i
        LEFT JOIN citations c ON i.id = c.snippet_id
        WHERE i.id IN ({",".join(map(str, idx))})
    """
    rows = execute_query(query)
    # print(f"rows: {rows}")
    # Group items by theme_id with their citations
    theme_items = {}
    for row in rows:
        id, source_file, sub_theme, snippet, supports, rejects, citation = row

        if sub_theme not in theme_items:
            theme_items[sub_theme] = []

        # Find if item already exists in the list
        item_exists = False
        for item in theme_items[sub_theme]:
            if item["id"] == id:
                # If citation exists, add to citations list
                if citation:
                    if "citations" not in item:
                        item["citations"] = []
                    item["citations"].append(citation)
                item_exists = True
                break

        if not item_exists:
            # Create new item entry
            new_item = {
                "id": id,
                "source_file": source_file,
                "snippet": snippet,
                "supports": supports,
                "rejects": rejects,
                "citations": [],
            }
            if citation:
                new_item["citations"].append(citation)
            theme_items[sub_theme].append(new_item)

    return theme_items


########################################################


def get_or_create_aggregated_themes(database_name: str, force_new=False):
    """
    Get existing aggregated themes from DB or create new ones.
    Args:
        database_name (str): Name of the database to use
        force_new (bool): If True, always create new aggregation regardless of existing data
    Returns:
        dict: Processed answer containing aggregated themes
    """
    # Check if we have existing aggregation
    if not force_new:
        query = "SELECT data FROM aggregated_themes ORDER BY created_at DESC LIMIT 1"
        existing = execute_query(query)
        if existing and existing[0][0]:  # Check if data exists and is not None/empty
            try:
                # If data is already a dict, return it directly
                if isinstance(existing[0][0], dict):
                    return existing[0][0]
                # Otherwise, try to parse it as JSON
                return json.loads(existing[0][0])
            except (json.JSONDecodeError, TypeError):
                # If data exists but is invalid JSON, force new aggregation
                pass

    # Create new aggregation if force_new=True or no valid data found
    processed_answer = aggregate_themes()

    # Store the new aggregation
    insert_query = """
        INSERT INTO aggregated_themes (data, created_at)
        VALUES (%s, CURRENT_TIMESTAMP)
    """
    execute_query(insert_query, (json.dumps(processed_answer),))
    return processed_answer

    return processed_answer


def aggregate_themes():
    """
    Aggregate the themes contained in the database into several clusters.
    Returns:
        dict: Processed answer containing aggregated themes
    """
    themes = execute_query("SELECT id, theme FROM knowledge_snippets")
    sthemes = [f"{theme[0]}. {theme[1]}" for theme in themes]

    user_prompt = aggregate_prompt.format(themes=sthemes)

    response = openai.beta.chat.completions.parse(
        model=model_name,
        messages=[{"role": "user", "content": user_prompt}],
        response_format={"type": "json_object"},
    )

    answer = response.choices[0].message.content
    return process_LLM_output(answer)


# answers = aggregate_themes()


# found_indices = find_item_indices(query, answers)
# found_indices

# theme_items = get_theme_items_from_db(query, answers)
# print(answers)
