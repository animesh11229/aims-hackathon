# 🎓 Campus Compass: The Intelligent RAG Assistant

An intelligent, user-friendly Retrieval-Augmented Generation (RAG) system designed to be the ultimate campus companion. It hooks directly into a **Google Drive folder**, allowing for an incredibly easy-to-update knowledge base, and uses a powerful LLM to answer student queries accurately.

---

## ✨ Key Features

- 🧠 **Intelligent RAG System** – Utilizes a sophisticated two-step process. First, it intelligently gathers relevant context from documents, and second, it uses that context to extract a precise, helpful answer for the user.  
- 📂 **Google Drive as a Database** – The entire knowledge base is a simple Google Drive folder. Updating information is as easy as dragging and dropping files. No complex database management needed!  
- 🏷️ **Smart File Tagging** – Use special tags like `$$SYSTEM$$` and `$$USER-NOTES$$` in your filenames to define their roles, helping the RAG system prioritize official documents over user-contributed notes when needed.  
- 📢 **Real-time Announcements** – A moderator can send an email with the subject line `"announcements"` to a dedicated email address, and the system can fetch and display these updates instantly.  
- 🤖 **LLM-Powered** – Leverages the power of Large Language Models (**Google’s Gemini**, for now) to understand queries and provide conversational, accurate answers.  

---

## ⚙️ How It Works

The system is built around a simple yet powerful architecture that makes it both effective and easy to maintain.

### **1. The Knowledge Base (Google Drive)**

The core of the system is a **shared Google Drive folder**. You create a folder hierarchy that makes sense for your institution. The RAG system intelligently scans this structure.

You can tag files to give the system hints about their content:

- `$$SYSTEM$$` – Marks official documents (e.g., syllabi, maps, official rules). Treated as the “source of truth.”  
- `$$USER-NOTES$$` – Marks user-contributed content like student lecture notes.  
- `$$USER-BOOK$$` – Marks textbook files.  

**Example folder structure:**
```bash
├── $$SYSTEM$$:timetable.pdf
├── about_clg
    ├── $$SYSTEM$$:Complete_Campus_Map.pdf
    ├── $$SYSTEM$$:NSUT_Campus_Guide.pdf
    ├── $$SYSTEM$$:Student_Life_Overview.pdf
├── maths
    ├── semister 1
        ├── $$SYSTEM$$:Syllabus_Math1.pdf
├── electrical engneering
    ├── semister1
        ├── $$SYSTEM$$:syllabus_EE_sem1.pdf

```

### **2. LLM Capabilities (Tools)**

The Large Language Model (LLM) is given specific tools to interact with the knowledge base:

- **Request Files for Context** – Looks up relevant information from official university documents on topics like navigation, academics, and campus life.  
- **Request Shareable File Links** – Provides a direct, shareable download link for a specific document, notes, or syllabus.  
- **Read Announcements** – Fetches and displays the latest announcements from the dedicated email channel.  



## 🚀 Getting Started

Follow these steps to set up and run your own instance of the **Campus Compass Assistant**.



### **Prerequisites**

- Python 3.9+  
- A Google Cloud Platform project  
- A dedicated Gmail account for announcements  



### **1. Clone the Repository**
```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```
2. Install Dependencies
pip install -r requirements.txt
You will need to create a requirements.txt file with libraries such as:
```bash
google-api-python-client
google-auth-httplib2
google-auth-oauthlib
python-dotenv
google-generativeai
```

3. Configure Google Drive & Service Account
Go to Google Cloud Console.

Create a new project or select an existing one.

Enable the Google Drive API.

Navigate to Credentials → Create Credentials → Service account.

Assign at least the Viewer role.

In the Keys tab, click Add Key → Create new JSON key.

Save and rename it to service-account.json, placing it in the root directory of your project.

IMPORTANT – Share your Google Drive folder with the service account email (e.g., my-service-account@my-project.iam.gserviceaccount.com).

4. Set Up Environment Variables
Create a .env file in the root directory:
```bash
# API Key for the LLM (Google Gemini)
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# Gmail account for fetching announcements
GMAIL="your-announcement-email@gmail.com"

# Gmail App Password (NOT your normal password)
# See: https://support.google.com/accounts/answer/185833
GMAIL_PASS="your_gmail_app_password"
```
5. Run the Application
```bash
python app.py
```
Now you can start asking Campus Compass questions! 🎉

💡 Example Use Cases
Navigation – “Where can I find the main library?”

Resource Finding – “Can you give me the link to the syllabus for Electrical Engineering?”

Notes Retrieval – “Find me Hitesh’s notes for the first CAD lecture.”

Stay Updated – “Are there any new announcements?”


