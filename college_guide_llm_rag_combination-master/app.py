from flask import Flask, render_template, request, session,jsonify
import llm_functions
app = Flask(__name__)
app.secret_key = 'super secret key!@#$@$%&^*(^&&$^*67586589924859023$#@%@#$%@#$%QWFKDSAFKEDEOFJDSAjdfhkjasflkj$@#%^%^'
llm_functions.initialize()
llm_functions.reload_hierarchy()
@app.route('/')
def index():
    session.clear()
    return render_template("main.html")

@app.route('/api', methods=['POST'])
def api():
    session.permanent = False
    llm_functions.initialize()

    # 1. Get the simple history from the session.
    simple_history = session.get('chat_history', [])

    # 2. Re-create the Gemini model for this request.
    chat_model = llm_functions.initialize_gemini_model(simple_history)

    # 3. Get the new message.
    user_message = request.json['message']

    # 4. Get the response from the model.
    response_gemini = llm_functions.gemini_main_response(user_message, chat_model)

    # 5. --- MODIFIED SECTION ---
    # Create a NEW simple history, keeping only 'user' and 'model' roles.
    # We use a list comprehension for a clean and efficient implementation.
    updated_simple_history = [
        {
            "role": content.role,
            "parts": [part.text for part in content.parts]
        }
        for content in chat_model.history
        if content.role in ('user', 'model')  # This condition filters out other roles
    ]

    # 6. Save the filtered, JSON-friendly list back to the session.
    session['chat_history'] = updated_simple_history

    # 7. Send the response back to the frontend.
    return jsonify({"response": response_gemini})


if __name__ == '__main__':
    app.run(debug=True)




'''to do
Tutoring mode add

Update for range of dates
$$DEBUG$$ fix
Give me notes from 10-08-2025
to 12-08-2025

Fix , book request

add nsut calender

Done all 😊
'''