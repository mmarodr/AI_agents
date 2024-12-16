import json
import logging

logger = logging.getLogger(__name__)

safe_globals = None
safe_locals = None

def run_python_code(code, variable_to_return) -> str:
    """
        This function to runs Python code in the current environment.
        If successful, returns the value of `variable_to_return` if provided otherwise returns a success message.
        If failed, returns an error message.

        Returns the value of `variable_to_return` if successful, otherwise returns an error message.

        :param inputs: The inputs to the function as a dictionary or a JSON string.
            :param code: The code to run.
            :param variable_to_return: The variable to return.
            :return: value of `variable_to_return` if successful, otherwise returns an error message.
    """
    try:
        logger.warning("PythonTools can run arbitrary code, please provide human supervision.")

        safe_globals: dict = globals()
        safe_locals: dict = locals()
        
        # if isinstance(inputs, str):
        #     inputs = json.loads(inputs)

        # code = inputs.get('code', '')
        # variable_to_return = inputs.get('variable_to_return')

        logger.debug(f"Running code:\n\n{code}\n\n")
        exec(code, safe_globals, safe_locals)

        if variable_to_return:
            variable_value = safe_locals.get(variable_to_return)
            if variable_value is None:
                return f"Variable {variable_to_return} not found"
            logger.debug(f"Variable {variable_to_return} value: {variable_value}")
            return str(variable_value)
        else:
            return "successfully ran python code"
    except Exception as e:
        logger.error(f"Error running python code: {e}")
        return f"Error running python code: {e}"
    
    