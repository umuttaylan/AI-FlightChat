# 🛫 FlightChat Agents — AI-Powered Flight Booking Simulation 🚀

Welcome, traveler!  
**FlightChat Agents** is a fun and educational demo project that simulates an AI-powered flight assistant.  
You can chat to search for flights, generate city images, send voice messages, and translate responses—all in one place!  
**Note:** This is a simulation. No real bookings are made and flight data may be mocked.

---

## ✨ What Can You Do?

- **Search for flights by chatting:**  
  Ask things like “Find me the cheapest flight from Istanbul to London next Friday.”
- **Generate city images:**  
  See an AI-generated image of your destination city.
- **Send voice messages:**  
  Speak into your microphone and your message will be transcribed.
- **Translate responses:**  
  Instantly translate AI replies into your preferred language.
- **Listen to responses:**  
  Let the AI read out the answers to you.

---

## 🚀 Quick Start

1. **Clone the repo and set up your environment:**
    ```bash
    git clone <repo-url>
    cd AI-ChatBot
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

2. **Configure your API keys:**
    ```bash
    # Edit the .env file and add your OpenAI, Anthropic, and Amadeus keys
    ```

3. **Run the app:**
    ```bash
    python app.py
    ```
    Then open [http://127.0.0.1:7860](http://127.0.0.1:7860) in your browser.

---

## 💡 How Does It Work?

- **GPT (OpenAI):**  
  Understands your messages, chats, and summarizes flight options.
- **Amadeus API:**  
  Fetches real flight data (or uses mock data if no API key is provided).
- **Claude (Anthropic):**  
  Translates responses into your chosen language.
- **DALL·E 3:**  
  Generates images of your destination city.
- **Gradio:**  
  Provides a simple and interactive web interface.

---

## 🧑‍💻 Example Prompts

- "I want to fly from Istanbul to Paris on September 15"
- "Show me cheap flights to Berlin next week"
- "Translate the answer to German" (Check the translate box and select a language)

---

## 🛠️ Notes & Tips

- **This is a demo project and a simulation.**  
  No real bookings are made. Flight data may be mocked if API keys are missing.
- Real-time prices require an Amadeus API key.
- Images and audio files are stored in `generated_images/` and `generated_audio/` folders.
- You can extend this project with better validation, caching, or NLP features.

---

## 🤖 Want to Contribute?

Pull requests and issues are welcome!  
Feel free to [open an issue](https://github.com/username/AI-ChatBot/issues) for questions or suggestions.

---

## License

MIT

---

**Your dream trip is just a message away—have
