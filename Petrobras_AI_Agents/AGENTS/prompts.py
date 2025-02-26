###### PROMPTS #######

prompt_json_format = [
        "Output must be in strict JSON format on a single line without any line breaks or additional text, or use \\n to break lines.",
        "Do not include explanations, formatting, or markers (e.g., `json` markers).",
        "Use valid JSON syntax with correctly escaped characters, especially quotes and control characters, to avoid decoding errors.",
        "Pay attention that "
        ]

#Noa sei se está sendo usado
llm_response_language = "**Always respond and articulate thoughts in '{language}'**"

llm_response_Instruction = [
        # "Include all parameters in your response.",
        # "Your response must be a dictionary with the parameters as key and the expected response for each key as instructected.",
        "Avoid dictionaries, lists or tables into your expected response, unless explicitly requested.",
        "Ensure all instructions for parameters are followed exactly to avoid penalties.",
        *prompt_json_format
        ]

llm_response_answer = [
    "Always stick to your goals, defined on your description, when retriving responses.",
    "Give relevant details, especially mentioning key elements related to the context.",
    "Always consider the user's input and the provided context, if available.",
    "Your answer may be a direct response or a task you are dalegating to another agent"
]

llm_response_next_agent = [
        "Select one agent from the dictionary below.",
        "Return only the exact agent name from the list."
        # "Avoid delegating tasks that you can execute directly."
        ]

llm_response_tool_choice = [
        "Select one tool from the list below.",
        "Return only the exact tool name from the list."
        ]

llm_response_tool_input = [
        "Define the input parameters for the chosen tool.",
        "Adjust the input based on the tool's description.",
        "The input can be a dictionary, string, or list, depending on the tool.",
        *prompt_json_format
        ]