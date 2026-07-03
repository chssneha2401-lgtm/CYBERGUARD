# Cyberbullying Detection App

A simple Machine Learning and NLP web application that classifies user-entered text as `bullying` or `non_bullying`.

## Features

- Text preprocessing with tokenization
- Naive Bayes classifier implemented in Python
- Cyberbullying / non-bullying prediction
- Confidence score and model score breakdown
- Clean Flask web interface
- Starter dataset included in `data/messages.csv`
- URL text extraction with private-network protection
- PDF, DOCX, TXT, CSV, and Markdown scanning
- Image OCR and audio/video speech transcription

## Run the App

```bash
py -B app.py
```

Then open:

```text
http://127.0.0.1:5000
```

Image scanning requires [Tesseract OCR](https://github.com/tesseract-ocr/tesseract). Audio and video scanning require `ffmpeg`; speech recognition also needs an internet connection.

## Project Structure

```text
app.py                 Flask application
model.py               ML/NLP classifier logic
data/messages.csv      Training dataset
templates/index.html   Web page
static/styles.css      Styling
requirements.txt       Python dependency list
```

## How It Works

The app trains a Multinomial Naive Bayes-style classifier from the CSV dataset when the server starts. The text entered by the user is tokenized, converted into word counts, and scored against both classes. The class with the higher probability is shown as the prediction.

For better accuracy, replace `data/messages.csv` with a larger labelled cyberbullying dataset using the same columns:

```csv
label,text
bullying,"example harmful message"
non_bullying,"example safe message"
```
