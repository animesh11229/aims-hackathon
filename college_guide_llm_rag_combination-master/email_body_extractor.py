# IMPORTANT: You need to install the 'imap-tools' library first.
# Run this command in your terminal: pip install imap-tools
from imap_tools import MailBox, A
from dotenv import load_dotenv
import os

load_dotenv(override=True)
gmail = os.getenv('GMAIL')
password = os.getenv('GMAIL_PASS')



def read_emails_with_subject_alternative(username=gmail, password=password, subject_to_find="announcements", imap_server="imap.gmail.com"):
    """
    Connects to an email account using the 'imap-tools' library,
    finds emails with a specific subject, and extracts their text content.

    Args:
        username (str): The email account username.
        password (str): The password for the email account.
                        For Gmail, it's highly recommended to use an "App Password".
        subject_to_find (str): The subject line to search for.
        imap_server (str): The IMAP server address. Defaults to Gmail's server.

    Returns:
        list: A list of strings, where each string is the body of a found email.
              Returns an empty list if no emails are found or an error occurs.
    """
    extracted_contents = []

    try:
        # Connect to the mailbox
        with MailBox(imap_server).login(username, password, 'INBOX') as mailbox:
            # Search for emails with the specified subject.
            # The 'A' (And) function creates the search criteria.
            # The search is case-insensitive by default.
            messages = mailbox.fetch(A(subject=subject_to_find))

            #print(f"Searching for emails with subject '{subject_to_find}'...")

            for msg in messages:
                #print(f"\n--- Processing Email ---")
                #print(f"From: {msg.from_}")
                #print(f"Subject: {msg.subject}")

                # The 'text' property automatically finds the plain text body
                if msg.text:
                    extracted_contents.append({"date":msg.date.strftime("%Y-%m-%d and time-%H:%M"), "content":msg.text.strip("\n")})
                    #print("Successfully extracted content.")
                else:
                    print("Could not extract plain text content from this email.")

    except Exception as e:
        # The library provides more descriptive error messages
        print(f"An error occurred: {e}")

    return extracted_contents


# --- EXAMPLE USAGE ---
if __name__ == '__main__':
    # ==============================================================================
    # IMPORTANT SECURITY NOTICE:
    # 1. DO NOT hardcode your password directly in the script in a real application.
    #    Use environment variables or a secure vault.
    # 2. For Gmail, you MUST enable 2-Factor Authentication and then create an
    #    "App Password". Using your regular Google password will NOT work and is
    #    less secure.
    #    How to create an App Password: https://support.google.com/accounts/answer/185833
    # ==============================================================================

    # --- Configuration ---
    # Replace with your details

    SUBJECT_TO_FIND = "announcements"


