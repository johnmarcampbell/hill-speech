from flask import Flask, render_template, request
from gensim.models import LdaModel
from gensim.corpora import Dictionary
from pymongo import MongoClient
from bokeh.embed import components
import pyLDAvis
import pickle
from datetime import datetime
import pandas as pd

from helpers import get_speaker_topics, get_topic_name, make_topic_plot, \
    score_doc, score_corpus, make_scoreVsTime_plot, get_speaker

from forms import GetSpeakerForm

DICTIONARY_PATH = 'models/dictionary_97-07_and_10-18.dict'
with open(DICTIONARY_PATH, 'rb') as f:
    dictionary = pickle.load(f)

MODEL_PATH = 'models/all_50topics.lda'
model = LdaModel.load(MODEL_PATH)

VIS_PATH = 'models/all_50topics.ldavis'
with open(VIS_PATH, 'rb') as f:
    vis = pickle.load(f)

app = Flask(__name__)
app.secret_key = 'dev_key'

# Index page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/speaker', methods=['GET', 'POST'])
def speaker():
    form = GetSpeakerForm()
    if form.validate_on_submit():
        speaker = form.name.data
        print("Speaker: " + speaker)
    else:
        speaker = 'kilmer'

    speaker_dict = get_speaker(speaker)

    topics = get_speaker_topics(model,speaker, dictionary)
    topics = [(get_topic_name(x[0]), x[1]) for x in topics]

    topics.sort(key=lambda x:x[1])
    labels = [x[0] for x in topics]
    vals = [x[1] for x in topics]

    p = make_topic_plot(labels, vals)
    script, div = components(p)

    return render_template('speaker.html', speaker=speaker_dict,
            script=script, div=div, form=form)

@app.route('/model')
def model_page():
    vis_html = pyLDAvis.prepared_data_to_html(vis)
    return render_template('model.html', vis_html=vis_html)

@app.route('/speaker/<speaker>/<topic>')
def speaker_topic_page(speaker, topic):
    client = MongoClient()
    db = client['congressional-record']
    speeches = db['speeches']
    # TODO: The speaker 'kilmer' is hard coded here. Change.
    search = {'speaker':'kilmer'}
    speaker_corpus = [(post['lemma'], datetime.strptime(post['date'], '%m/%d/%Y')) for post in speeches.find(search) ]
    client.close()

    # TODO: The topic number '3' is hard coded here. Change.
    community_docs = score_corpus(speaker_corpus, model, dictionary, 3)
    community_docs.sort(reverse=True)
    previews = community_docs[:3]
    previews = [('{0:.2f}'.format(p[0]), p[1], p[2]) for p in previews]
    previews = [(p[0], p[1], p[2][0].upper() + p[2][1:]) for p in previews]
    df = pd.DataFrame(community_docs, columns=['score', 'date', 'text'])
    p = make_scoreVsTime_plot(df)
    script, div = components(p)

    return render_template('speaker_topic.html', speaker=speaker,
            script=script, div=div, preview=previews)

if __name__ == '__main__':
	app.run(port=5000, debug=True)
