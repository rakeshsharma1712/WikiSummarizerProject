# doing necessary imports
import threading
import io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

from logger_class import getLog
from flask import Flask, render_template, request, jsonify, Response, url_for, redirect
from flask_cors import CORS, cross_origin
import pandas as pd
from mongoDBOperations import MongoDBManagement
from WikiScrapping import WikiScrapper
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager

rows = {}
collection_name = None

logger = getLog('wikiscrap.py')

free_status = True
db_name = 'Wiki-Scrapper'

app = Flask(__name__)  # initialising the flask app with the name 'app'

#For selenium driver implementation on heroku
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument("disable-dev-shm-usage")


#To avoid the time out issue on heroku
class threadClass:

    def __init__(self, searchString, scrapper_object):
        self.searchString = searchString
        self.scrapper_object = scrapper_object
        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True  # Daemonize thread
        thread.start()  # Start the execution

    def run(self):
        global collection_name, free_status
        free_status = False
        collection_name = self.scrapper_object.getSummaryToDisplay(searchString=self.searchString,username='mongodb',
                                                                   password='mangodb')

        logger.info("Thread run completed (app)")
        free_status = True



@app.route('/', methods=['POST', 'GET'])
@cross_origin()
def index():
    if request.method == 'POST':
        global free_status
        ## To maintain the internal server issue on heroku
        if free_status != True:
            return "This website is executing some process. Kindly try after some time..."
        else:
            free_status = True

        searchString = request.form['content'].strip()  # obtaining the search string entered in the form
        try:
            scrapper_object = WikiScrapper(executable_path=ChromeDriverManager().install(),
                                               chrome_options=chrome_options)
            mongoClient = MongoDBManagement(username='mongodb', password='mongodb')

            if mongoClient.isCollectionPresent(collection_name=searchString, db_name=db_name):
                rows = mongoClient.findAllRecords(db_name=db_name, collection_name=searchString)
                logger.info(f'{searchString} : Found in DB (app)')

                page_data = [i for i in rows]

                image_list = []
                ref_list = []
                for dict in page_data:
                    for key,value in dict.items():
                        if key == 'summary':
                            summary = value
                        elif key == 'images':
                            for l in value.values():
                                image_list.append(l)
                        elif key == 'reference':
                            for l in value.values():
                                ref_list.append(l)

                logger.info(f"{searchString} : Read DB and formatted result (app)")

                return render_template('results.html', reSummary=summary,reImage=image_list,reRef=ref_list)
            else:
                logger.info(f"{searchString} : Not found in DB (app)")
                scrapper_object.openUrl("https://www.wikipedia.org/")

                scrapper_object.searchKeyword(searchString=searchString)
                logger.info(f"Search begins for {searchString} (app)")

                threadClass(searchString=searchString, scrapper_object=scrapper_object)
                logger.info(f"{searchString} : Successfully extracted details (app)")

                return redirect(url_for('wikisummary'))
        except Exception as e:
            raise Exception("(app.py) - Something went wrong while rendering all the details of product.\n" + str(e))

    else:
        return render_template('index.html')


@app.route('/wikisummary', methods=['GET'])
@cross_origin()
def wikisummary():
    try:
        global collection_name

        if collection_name is not None:
            logger.info(f"Landed in wikisummary Para")
            scrapper_object = WikiScrapper(executable_path=ChromeDriverManager().install(),
                                               chrome_options=chrome_options)
            mongoClient = MongoDBManagement(username='mongodb', password='mongodb')
            rows = mongoClient.findAllRecords(db_name="Wiki-Scrapper", collection_name=collection_name)

            proceed = True
            try:
                page_data = [i for i in rows]
            except:
                proceed = False

            if proceed == True:
                logger.info(f"Record read from DB (wikisummary)")
                collection_name = None

                image_list = []
                ref_list = []
                for dict in page_data:
                    for key, value in dict.items():
                        if key == 'summary':
                            summary = value
                        elif key == 'images':
                            for l in value.values():
                                image_list.append(l)
                        elif key == 'reference':
                            for l in value.values():
                                ref_list.append(l)

                logger.info(f"Formatted result (wikisummary)")
                scrapper_object.closeConnection()
                logger.info(f"Closed connection (wikisummary)")

                return render_template('results.html', reSummary=summary, reImage=image_list, reRef=ref_list)
            else:
                logger.info(f"Not able to search input keyword (wikisummary)")
                summary = 'Entered keyword is not found on Wikipedia. Please try with correct/another keyword.'
                return render_template('results.html', reSummary=summary)
        else:
            return render_template('results.html', rows=None)
    except Exception as e:
        raise Exception("(wikisummary) - Something went wrong on retrieving wikisummary.\n" + str(e))


if __name__ == "__main__":
    app.run()  # running the app on the local machine on port 8000
