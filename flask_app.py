from sentence_transformers import SentenceTransformer, util
import torch
import pickle
from langdetect import detect
from flask import Flask, request, jsonify, send_from_directory
import requests

app = Flask(__name__)



# Load the saved model
model_save_path = 'model'
model = SentenceTransformer(model_save_path)

# Load embeddings, questions, and answers
with open('model/embeddings.pkl', 'rb') as f:
    embeddings = pickle.load(f, encoding='latin1')

with open('model/questions.pkl', 'rb') as f:
    questions = pickle.load(f, encoding='latin1')

with open('model/answers.pkl', 'rb') as f:
    answers = pickle.load(f, encoding='latin1')

with open('model/languages.pkl', 'rb') as f:
    languages = pickle.load(f, encoding='latin1')

# Function to get embeddings for a list of questions
def get_embeddings(model, questions):
    return model.encode(questions, convert_to_tensor=True)

# Function to find the most similar question and return its answer
def find_most_similar_question(new_question, model, questions, embeddings, answers, languages):
    new_embedding = get_embeddings(model, [new_question])
    cos_scores = util.pytorch_cos_sim(new_embedding, embeddings)[0]
    top_results = torch.topk(cos_scores, k=1)
    for score, idx in zip(top_results[0], top_results[1]):
        if score < 0.7 or detect(new_question) != languages[idx]:
            if detect(new_question) == 'fr':
                return "Je n'ai pas de réponse."
            elif detect(new_question) == 'en':
                return "I don't have an answer."
        return answers[idx]

# In-memory storage for conversation history
conversation_history = []

@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.json
    user_question = data['question']

    # Find the most similar question
    response_text = find_most_similar_question(user_question, model, questions, embeddings, answers, languages)

    # Save to conversation history
    conversation_history.append({'user': user_question, 'bot': response_text})
    if detect(response_text) == 'en':
        voice =  {'id': 2021, 'voice_id': 'en-US-Neural2-I', 'gender': 'Male', 'language_code': 'en-US', 'language_name': 'US English', 'voice_name': 'Maxwell', 'sample_text': 'Hello, hope you are having a great time making your video.', 'sample_audio_url': 'https://s3.ap-south-1.amazonaws.com/invideo-uploads-ap-south-1/speechen-US-Neural2-I16831901125770.mp3', 'status': 2, 'rank': 0, 'type': 'google_tts', "isPlaying": False}
    else :
        voice =  {'id': 2039, 'voice_id': 'fr-FR-Neural2-B', 'gender': 'Male', 'language_code': 'fr-FR', 'language_name': 'French', 'voice_name': 'Alexandre', 'sample_text': "Bonjour, j'espère que vous passez un bon moment à faire votre vidéo.", 'sample_audio_url': 'https://s3.ap-south-1.amazonaws.com/invideo-uploads-ap-south-1/speechfr-FR-Neural2-B16831901134250.mp3', 'status': 2, 'rank': 0, 'type': 'google_tts' , "isPlaying": False}
    # Convert text response to audio using RapidAPI
    url = "https://realistic-text-to-speech.p.rapidapi.com/v3/generate_voice_over_v2"
    payload = {
        "voice_obj": voice,
        "json_data": [
            {
                "block_index": 0,
                "text": response_text
            }
        ]
    }
    headers = {
        "x-rapidapi-key": "067d986cffmshe91e183975a1289p1e0d3djsnb73769da8460",
        "x-rapidapi-host": "realistic-text-to-speech.p.rapidapi.com",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    audio_response = response.json()
    if response.status_code == 200 and audio_response:
        audio_url = audio_response[0]['link']
    else:
        audio_url = None
    print(audio_url)  # Log the audio URL to verify

    return jsonify({'response_text': response_text, 'audio_url': audio_url, 'history': conversation_history})

if __name__ == '__main__':
    app.run(debug=True)

