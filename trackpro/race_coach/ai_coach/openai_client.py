"""Client for interacting with the OpenAI API for coaching advice."""

import os
import logging
from openai import OpenAI, OpenAIError

logger = logging.getLogger(__name__)

def get_api_key() -> str:
    """
    Retrieves the OpenAI API key from environment variables.

    Returns:
        The API key or None if not found.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY environment variable not set.")
    return api_key

def get_coaching_advice(current_telemetry: dict, superlap_telemetry: dict, model: str = "gpt-4-turbo") -> str:
    """
    Gets coaching advice from OpenAI based on telemetry comparison.

    Args:
        current_telemetry (dict): The driver's current telemetry point.
        superlap_telemetry (dict): The corresponding superlap telemetry point.
        model (str): The OpenAI model to use.

    Returns:
        A string containing the coaching advice, or an empty string if an error occurs.
    """
    api_key = get_api_key()
    if not api_key:
        return ""

    client = OpenAI(api_key=api_key)

    # Constructing a detailed prompt for the AI
    system_prompt = (
        "You are an expert race car driving coach. Your goal is to help a driver achieve a 'superlap' time by "
        "providing real-time, concise, and actionable advice. You will be given a snapshot of the driver's current "
        "telemetry and the equivalent telemetry from the superlap at the same point on the track. "
        "Compare the two and give one single, clear instruction to the driver. The advice should be very short, "
        "like a real coach would say over the radio. Focus on the most critical difference. "
        "For example: 'Brake later here', 'More throttle on exit', 'Ease off the steering', 'Carry more speed through this section'. "
        "Do not greet the user or add any conversational fluff. Just give the coaching command."
    )

    # Helper function to safely format telemetry values
    def format_value(value, default='N/A'):
        try:
            if value is None or value == 'N/A':
                return default
            return f"{float(value):.2f}"
        except (ValueError, TypeError):
            return default
    
    # Format the telemetry data for the prompt
    user_prompt = (
        "Analyze this telemetry data and provide a coaching command:\n\n"
        "Driver's Telemetry:\n"
        f"- Speed: {format_value(current_telemetry.get('speed'))} km/h\n"
        f"- Throttle: {format_value(current_telemetry.get('throttle'))}\n"
        f"- Brake: {format_value(current_telemetry.get('brake'))}\n"
        f"- Steering: {format_value(current_telemetry.get('steering'))}\n\n"
        "Superlap Telemetry (the target):\n"
        f"- Speed: {format_value(superlap_telemetry.get('speed'))} km/h\n"
        f"- Throttle: {format_value(superlap_telemetry.get('throttle'))}\n"
        f"- Brake: {format_value(superlap_telemetry.get('brake'))}\n"
        f"- Steering: {format_value(superlap_telemetry.get('steering'))}\n"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=50,  # Keep the response short and concise
        )
        advice = response.choices[0].message.content.strip()
        logger.info(f"OpenAI generated advice: {advice}")
        return advice
    except OpenAIError as e:
        logger.error(f"OpenAI API Error: {e}")
        return ""
    except Exception as e:
        logger.error(f"An unexpected error occurred in get_coaching_advice: {e}")
        return ""

if __name__ == '__main__':
    # Example usage for testing
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing OpenAI client...")

    # Mock telemetry data
    mock_driver_telemetry = {'speed': 150.5, 'throttle': 0.9, 'brake': 0.1, 'steering': 0.05}
    mock_superlap_telemetry = {'speed': 155.0, 'throttle': 1.0, 'brake': 0.0, 'steering': 0.04}

    if not get_api_key():
        logger.error("Cannot run test: OPENAI_API_KEY is not set.")
        logger.info("Please set the environment variable and try again.")
    else:
        advice = get_coaching_advice(mock_driver_telemetry, mock_superlap_telemetry)
        if advice:
            logger.info(f"Successfully received coaching advice: '{advice}'")
        else:
            logger.error("Failed to get coaching advice.") 