import logging
from PyQt6.QtWidgets import QMessageBox
from ..database.supabase_client import get_supabase_client
from ..config import CURRENT_TERMS_VERSION
from ..ui.terms_dialog import TermsDialog

logger = logging.getLogger(__name__)

def check_and_prompt_for_terms(user_id, parent_widget=None):
    """
    Checks if a user has accepted the latest terms and prompts them if not.
    This is a self-contained function to be called after login.

    Args:
        user_id (str): The ID of the user to check.
        parent_widget (QWidget): The parent widget for the dialog.

    Returns:
        bool: True if the user has accepted the terms or accepts them now.
              False if the user declines or an error occurs.
    """
    try:
        if _user_has_accepted_latest_terms(user_id):
            return True

        logger.info(f"User {user_id} needs to accept the latest terms of service.")
        dialog = TermsDialog(parent=parent_widget)
        dialog.exec()

        if dialog.accepted:
            logger.info(f"User {user_id} accepted the terms.")
            if _update_user_terms_acceptance(user_id):
                return True
            else:
                QMessageBox.critical(parent_widget, "Error", "Could not save your acceptance. Please contact support.")
                return False
        else:
            logger.warning(f"User {user_id} declined the terms of service.")
            QMessageBox.warning(parent_widget, "Agreement Required", "You must accept the User Agreement to continue.")
            return False

    except Exception as e:
        logger.error(f"An unexpected error occurred during terms check for user {user_id}: {e}", exc_info=True)
        QMessageBox.critical(parent_widget, "Error", "An error occurred while checking the user agreement. Please try again.")
        return False

def _user_has_accepted_latest_terms(user_id):
    """Checks the database to see if the user's acceptance is up-to-date."""
    try:
        client = get_supabase_client()
        if not client:
            logger.error("Supabase client not available for terms check.")
            return False

        response = client.table("user_details").select("terms_accepted, terms_version_accepted").eq("user_id", user_id).execute()

        if response.data:
            details = response.data[0]
            terms_accepted = details.get("terms_accepted", False)
            version_accepted = details.get("terms_version_accepted", "0")
            
            try:
                is_up_to_date = terms_accepted and int(version_accepted) >= CURRENT_TERMS_VERSION
                if is_up_to_date:
                    logger.info(f"User {user_id} has already accepted terms version {version_accepted}.")
                return is_up_to_date
            except (ValueError, TypeError):
                return False
        return False
    except Exception as e:
        logger.error(f"Database error checking terms acceptance for user {user_id}: {e}")
        # To be safe, assume they haven't accepted if there's an error.
        return False

def _update_user_terms_acceptance(user_id):
    """Updates the database to record the user's acceptance of the current terms."""
    try:
        client = get_supabase_client()
        if not client:
            logger.error("Supabase client not available for terms update.")
            return False

        update_data = {
            "terms_accepted": True,
            "terms_version_accepted": str(CURRENT_TERMS_VERSION),
            "user_id": user_id
        }
        
        response = client.table("user_details").upsert(update_data).execute()

        if response.data:
            logger.info(f"Successfully updated terms acceptance for user {user_id}.")
            return True
        else:
            logger.error(f"Failed to update terms acceptance for user {user_id}: {getattr(response, 'error', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"Database error updating terms acceptance for user {user_id}: {e}")
        return False 