from bs4 import BeautifulSoup
from selenium import webdriver
from RepositoryForObject import ObjectRepository
from selenium.webdriver.common.by import By
import pandas as pd

from mongoDBOperations import MongoDBManagement
from gensim.summarization import summarize
import requests
from logger_class import getLog


class WikiScrapper:

    def __init__(self, executable_path, chrome_options):
        """
        This function initializes the web browser driver
        :param executable_path: executable path of chrome driver.
        """
        try:
            self.driver = webdriver.Chrome(executable_path=executable_path, chrome_options=chrome_options)
        except Exception as e:
            raise Exception(f"(__init__): Something went wrong on initializing the webdriver object.\n" + str(e))


    def getLocatorsObject(self):
        """
        This function initializes the Locator object and returns the locator object
        """
        try:
            locators = ObjectRepository()
            return locators
        except Exception as e:
            raise Exception(f"(getLocatorsObject) - Could not find locators\n" + str(e))

    def findElementByXpath(self, xpath):
        """
        This function finds the web element using xpath passed
        """
        try:
            element = self.driver.find_element(By.XPATH, value=xpath)
            return element
        except Exception as e:
            raise Exception(f"(findElementByXpath) - XPATH provided was not found.\n" + str(e))

    def findElementByClass(self, classpath):
        """
        This function finds web element using Classpath provided
        """
        try:
            element = self.driver.find_element(By.CLASS_NAME, value=classpath)
            return element
        except Exception as e:
            raise Exception(f"(findElementByClass) - ClassPath provided was not found.\n" + str(e))

    def findElementByTag(self, tag_name):
        """
        This function finds web element using tag_name provided
        """
        try:
            element = self.driver.find_elements_by_tag_name(tag_name)
            return element
        except Exception as e:
            raise Exception(f"(findElementByTag) - ClassPath provided was not found.\n" + str(e))

    def findingElementsFromPageUsingClass(self, element_to_be_searched):
        """
        This function finds all element from the page.
        """
        try:
            result = self.driver.find_elements(By.CLASS_NAME, value=element_to_be_searched)
            return result
        except Exception as e:
            raise Exception(
                f"(findingElementsFromPageUsingClass) - Something went wrong on searching the element.\n" + str(e))

    def findingElementsFromPageUsingCSSSelector(self, element_to_be_searched):
        """
        This function finds all element from the page.
        """
        try:
            result = self.driver.find_elements(By.CSS_SELECTOR, value=element_to_be_searched)
            return result
        except Exception as e:
            raise Exception(
                f"(findingElementsFromPageUsingClass) - Something went wrong on searching the element.\n" + str(e))

    def openUrl(self, url):
        """
        This function open the particular url passed.
        :param url: URL to be opened.
        """
        try:
            if self.driver:
                self.driver.get(url)
                return True
            else:
                return False
        except Exception as e:
            raise Exception(f"(openUrl) - Something went wrong on opening the url {url}.\n" + str(e))



    def generateTitle(self, search_string):
        """
        This function generatesTitle for the products searched using search string
        :param search_string: product to be searched for.
        """
        try:
            title = search_string + "- Summary from Wiki"
            return title
        except Exception as e:
            raise Exception(f"(generateTitle) - Something went wrong while generating complete title.\n" + str(e))



    def wait(self):
        """
        This function waits for the given time
        """
        try:
            self.driver.implicitly_wait(2)
        except Exception as e:
            raise Exception(f"(wait) - Something went wrong.\n" + str(e))



    def frameToDataSet(self, response):
        """
        This function frames the column to dataframe.
        """
        try:
            data_frame2 = pd.DataFrame()
            for column_name, value in response.items():
                if column_name == 'product_searched' or column_name == 'input_keyword' or column_name == 'price' or column_name == 'discount_percent' or column_name == 'offer_details' or column_name == 'EMI':
                    continue
                else:
                    flatten_result = [values for lists in response[column_name] for values in lists]
                    data_frame2.insert(0, column_name, flatten_result)
            return data_frame2
        except Exception as e:
            raise Exception(
                f"(dataGeneration) - Something went wrong on creating data frame and data for column.\n" + str(e))


    def saveDataFrameToFile(self, dataframe, file_name):
        """
        This function saves dataframe into filename given
        """
        try:
            dataframe.to_csv(file_name)
        except Exception as e:
            raise Exception(f"(saveDataFrameToFile) - Unable to save data to the file.\n" + str(e))

    def closeConnection(self):
        """
        This function closes the connection
        """
        try:
            self.driver.close()
        except Exception as e:
            raise Exception(f"(closeConnection) - Something went wrong on closing connection.\n" + str(e))

    def getSummaryToDisplay(self, searchString, username, password):
        """
        This function returns the summary of given input
        """
        try:
            logger = getLog('wikiscrap.py')

            search = searchString
            mongoClient = MongoDBManagement(username=username, password=password)
            locator = self.getLocatorsObject()

            input_keyword = searchString
            print(input_keyword)

            db_search = mongoClient.findfirstRecord(db_name="Wiki-Scrapper",
                                                    collection_name=searchString,
                                                    query={'input_keyword': input_keyword})
            if db_search is not None:
                logger.info(f"{searchString} : Found in DB (scrapper)")
            else:
                logger.info(f"{searchString} : Not found in DB (scrapper)")

            ### Get Summary of webpage
            summary = self.pageSummary()
            logger.info(f"{searchString} : Summary extracted (scrapper)")

            ### Get all the references of webpage
            page = self.openUrlSoup(url="https://en.wikipedia.org/wiki/", searchString=searchString)
            soup = self.extractSoup(page)

            ref_list = soup.find_all('cite', class_="citation")    # Get all links under 'References'
            ref_url_list = self.extractRef(ref_list=ref_list)      #Prepare a formatted reference link
            logger.info(f"{searchString} : Reference links extracted (scrapper)")

            page = []
            soup = []
            ref_list = []


            # Get all the images from webpage
            #open URL
            self.openUrl(url="https://en.wikipedia.org/wiki/" + searchString)
            self.wait()

            try:
                img_urls = self.extractImageLink()
                logger.info(f"{searchString} : Image links extracted (scrapper)")

                result = self.formatResult(images=img_urls, summary=summary, ref=ref_url_list)
                logger.info(f"{searchString} : Result formatted (scrapper)")

                # Insert Result to DB
                mongoClient.insertRecord(db_name="Wiki-Scrapper",collection_name=searchString,record=result)
                logger.info(f"{searchString} : Record inserted in DB (scrapper)")
            except:
                logger.info(f"{searchString} : Failed in while extracting image links (scrapper)")


            return search
        except Exception as e:
            raise Exception(f"(getSummaryToDisplay) - Something went wrong on yielding data.\n" + str(e))

    def searchKeyword(self, searchString):
        """
        This function helps to search product using search string provided by the user
        """
        try:
            locator = self.getLocatorsObject()
            search_box_path = self.findElementByXpath(xpath=locator.getInputSearchArea())
            search_box_path.send_keys(searchString)
            search_button = self.findElementByXpath(xpath=locator.getSearchButton())
            search_button.click()
            return True
        except Exception as e:
            # self.driver.refresh()
            raise Exception(f"(searchKeyword) - Something went wrong on searching.\n" + str(e))


    def removeNos(self, string, count):
        """
        This function helps to remove [1],[2],[3] numbers as per the count provided by user
        """
        try:
            char = []
            new_string = string
            for number in range(count):
                char.append('[' + str(number) + ']')

            for j in char:
                new_string = new_string.replace(j, '')

            char=[]

            return new_string
        except Exception as e:
            raise Exception(f"(removeNos) - Something went wrong while removing numbers.\n" + str(e))


    def removeNs(self, string):
        """
        This function helps to remove '\n' from summary
        """
        try:
            return string.replace('\n',' ')
        except Exception as e:
            raise Exception(f"(removeNs) - Something went wrong while removing Ns.\n" + str(e))


    def openUrlSoup(self, url,searchString):
        """
        This function open the particular url passed using Beautifulsoup.
        :param url: URL to be opened, searchString: string to be searched on URL.
        """
        try:
            page = requests.get(url+searchString)
            return page
        except Exception as e:
            raise Exception(f"(openUrlSoup) - Something went wrong on opening the url soup {url}.\n" + str(e))


    def extractSoup(self, page):
        """
        This function extracts soup for an input Beautifulsoup webpage.
        :param page: webpage from which soup should be extracted.
        """
        try:
            soup = BeautifulSoup(page.text, 'html.parser')

            return soup
        except Exception as e:
            raise Exception(f"(extractSoup) - Something went wrong on extracting soup.\n" + str(e))

    def pageSummary(self):
        """
        This function extracts content from a webpage and returns a summary of it.
        """
        try:
            page_text = self.findElementByTag('p')
            p_tags_text = [tag.text.strip() for tag in page_text]

            # Filter out sentences that contain newline characters '\n' or don't contain periods.
            sentence_list = [sentence for sentence in p_tags_text if not '\n' in sentence]
            sentence_list = [sentence for sentence in sentence_list if '.' in sentence]

            # Combine list items into string.
            article = ' '.join(sentence_list)

            try:
                article = self.removeNos(string=article, count=500)
            except:
                raise Exception(f"(pageSummary) - Error in removeNos().\n" + str(e))

            # Summarize webpage content
            try:
                summary = summarize(article, word_count=100)
            except:
                summary = summarize(article, ratio=0.1)

            # Remove unwanted \n from text
            summary = self.removeNs(string=summary)

            page_text = []
            p_tags_text = []
            sentence_list = []
            article = ''

            return summary
        except Exception as e:
            raise Exception(f"(pageSummary) - Something went wrong while formating result.\n" + str(e))

    def extractRef(self, ref_list):
        """
        This function extracts links and corresponding description from HTML list.
        :param ref_list: a list of HTML links.
        """
        try:
            url_list = {}
            url_pkg = []
            count = 0

            for ref_tag in ref_list:
                all_links = ref_tag.find_all('a')

                for link in all_links:
                    ref_url = link.get('href')
                    if ref_url[0:2] != '/w':
                        url_pkg.append(ref_url)
                        desc = self.findRefDesc(link=link)
                        desc = self.cleanString(string=desc)
                        url_pkg.append(desc)
                        url_list[str(count)] = url_pkg

                        count += 1
                        url_pkg = []

            all_links = []

            return url_list
        except Exception as e:
            raise Exception(f"(extractRef) - Something went wrong on extracting refernce.\n" + str(e))


    def cleanString(self, string):
        """
        This function removes the unwanted characters from input string.
        :param string: string from which unwanted characters should be removed.
        """
        try:
            cleanString = string.replace('\"', '').replace('"', '').replace('....', '').replace('...', '').replace(
                '..', '').replace("<i>", '').replace("</i>", "")


            return cleanString
        except Exception as e:
            raise Exception(f"(cleanString) - Something went wrong on cleaning string.\n" + str(e))


    def findRefDesc(self, link):
        """
        This function extracts description of a href for an HTML link.
        :param link: href link from which description to be extracted.
        """
        try:
            str_link = str(link)

            pos1 = str_link.find('">') + 2
            pos2 = str_link.find('</a>')

            if pos1 == -1:
                desc = 'Refernce link'
            else:
                desc = str_link[pos1:pos2]

            return desc
        except Exception as e:
            raise Exception(f"(findRefDesc) - Something went wrong while finding ref desc.\n" + str(e))

    def extractImageLink(self):
        """
        This function extracts all the image URLs for wikipedia webpage.
        """
        try:
            # Get image links
            img_urls = {}
            count = 0
            # Get first image
            try:
                imgResults = self.findElementByXpath('//*[@id="mw-content-text"]/div[1]/table[1]/tbody/tr[2]/td/a/img')
            except:
                imgResults = self.findElementByXpath(
                    '//*[@id="mw-content-text"]/div[1]/table[2]/tbody/tr[2]/td/a/img')

            imgResults.click()
            self.wait()

            actual_image = imgResults
            if actual_image.get_attribute('src') and 'https' in actual_image.get_attribute('src'):
                img_urls[str(count)] = actual_image.get_attribute('src')
                count = count + 1

            # Get other images
            prev_image = actual_image
            while 1 == 1:
                next_button = self.findElementByXpath('/html/body/div[7]/div/div[1]/button[4]')
                try:
                    next_button.click()
                    self.wait()
                    actual_image = self.findElementByXpath('/html/body/div[7]/div/div[2]/div/div[1]/img')
                except:
                    actual_image = prev_image

                if actual_image == prev_image:
                    break

                try:
                    if actual_image.get_attribute('src') and 'https' in actual_image.get_attribute('src'):
                        image_link = actual_image.get_attribute('src')
                        img_urls[str(count)] = image_link
                        count = count + 1
                        prev_image = actual_image
                except:
                    break

            return img_urls
        except Exception as e:
            raise Exception(f"(extractImageLink) - Something went wrong while getting image link.\n" + str(e))

    def formatResult(self, images, summary, ref):
        """
        This function format result for output webpage.
        :param images: list of image URLs, summary: summary of webpage, ref: list of reference URLs.
        """
        try:
            result = {}
            result['images'] = images
            result['summary'] = summary
            result['reference'] = ref

            return result
        except Exception as e:
            raise Exception(f"(formatResult) - Something went wrong while formatting result.\n" + str(e))
