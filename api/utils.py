# api/utils.py
import json

def parse_abbyy_response(raw_data):
    """
    Parses the verbose JSON from ABBYY Vantage and extracts only the
    clean field names and their values.
    """
    clean_data = {}
    try:
        fields = raw_data['Transaction']['Documents'][0]['ExtractedData']['RootObject']['Fields']
        for field in fields:
            field_name = field.get('Name')
            field_list = field.get('List')
            if not field_name or not field_list:
                continue
            
            if field_name == 'techSpecs':
                clean_data[field_name] = []
                for row in field_list:
                    row_data = {}
                    row_columns = row.get('Value', {}).get('Fields', [])
                    for column in row_columns:
                        column_name = column.get('Name')
                        column_list = column.get('List')
                        if column_name and column_list:
                            row_data[column_name] = column_list[0].get('Value')
                    if row_data:
                        clean_data[field_name].append(row_data)
            else:
                clean_data[field_name] = field_list[0].get('Value')
    except (KeyError, IndexError, TypeError) as e:
        print(f"Error parsing ABBYY response: {e}")
        return {"error": "Failed to parse the ABBYY JSON structure."}
    return clean_data

def parse_gemini_response(response_data):
    """
    Parses the response from a Gemini API call, automatically handling
    both standard 'text' responses and structured 'functionCall' responses.
    """
    if not response_data.get('candidates'):
        block_reason = response_data.get('promptFeedback', {}).get('blockReason', 'Unknown')
        raise ValueError(f"Response blocked by safety filters. Reason: {block_reason}")
    try:
        content = response_data['candidates'][0]['content']
        part = content['parts'][0]
        if 'functionCall' in part:
            return part['functionCall']['args']
        elif 'text' in part:
            cleaned_json_string = part['text'].strip()
            if not cleaned_json_string:
                raise ValueError("Gemini returned an empty text response.")
            return json.loads(cleaned_json_string)
        else:
            raise ValueError(f"Unexpected Gemini response format. Content: {content}")
    except (KeyError, IndexError) as e:
        raise ValueError(f"Failed to parse Gemini's response structure. Error: {e}")