# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Recursively extracts the text from a Google Doc.
"""
import googleapiclient.discovery as discovery
from httplib2 import Http
import create_service
import os
import re

SCOPES = ['https://www.googleapis.com/auth/documents.readonly']

def sanatize(string): 
    string = re.sub('(\xa0|\x0b|\v)', ' ', string)
    string = re.sub('\x0c', '\n', string)
    string = re.sub('\n+', '\n', string)
    string = re.sub(' +', ' ', string)
    string = re.sub(' \n', '\n', string)
    return string


def read_paragraph_element(element):
    """Returns the text in the given ParagraphElement.

        Args:
            element: a ParagraphElement from a Google Doc.
    """
    text_run = element.get('textRun')
    if not text_run:
        return ''
    return text_run.get('content')


def read_structural_elements(elements, print_header=False):
    """Recurses through a list of Structural Elements to read a document's text where text may be
        in nested elements.

        Args:
            elements: a list of Structural Elements.
    """
    global contentTree
    global currentParentTypes
    global headers
    global hId

    if print_header:
        # reset headers when its done
        oldHeaders = headers.copy()
        oldCurrentParentTypes = currentParentTypes.copy()
        oldHId = hId
    text = ''
    for value in elements:
        elementText = ''
        if 'paragraph' in value:
            headingId = value.get('paragraph').get('paragraphStyle').get('headingId')
            type = value.get('paragraph').get('paragraphStyle').get('namedStyleType')
            if headingId:
                if type in currentParentTypes:
                    currentParentTypes.index(type)
                    i = currentParentTypes.index(type)
                    currentParentTypes = currentParentTypes[:i]
                    headers = headers[:i]
                currentParentTypes.append(type)
                hId = headingId

            elements = value.get('paragraph').get('elements')
            for elem in elements:
                elementText += read_paragraph_element(elem)

            if headingId:
                elementText = elementText.replace('\n', ' ')
                elementText = sanatize(elementText).strip()
                if elementText:
                    headers.append(elementText)
                if not print_header:
                    continue
        elif 'table' in value:
            # The text in table cells are in nested Structural Elements and tables may be
            # nested.
            table = value.get('table')
            rows = table.get('tableRows')
            for i in range(len(rows)):
                row = rows[i]
                cells = row.get('tableCells')
                if i == 0:
                    firstRow = "|"
                    sep = "|"
                    for cell in cells:
                        c = read_structural_elements(cell.get('content'), True).strip("\n")
                        sep += '-' * len(c) + "|"
                        firstRow += c + "|"
                    elementText += firstRow + os.linesep + sep + os.linesep
                else:
                    elementText += "|"
                    for cell in cells:
                        elementText += read_structural_elements(cell.get('content'), True).strip("\n")
                        elementText += "|"
                    elementText += os.linesep

        elif 'tableOfContents' in value:
            # The text in the TOC is also in a Structural Element.
            # toc = value.get('tableOfContents')
            # text += read_structural_elements(toc.get('content'))
            # no new information here, so ignore
            continue

        if not sanatize(elementText).strip():
            continue

        text += sanatize(elementText) + os.linesep
        if contentTree.get(hId):
            contentTree[hId]["text"] += sanatize(elementText)
        else:
            contentTree[hId] = {"headers": headers, "text": sanatize(elementText), "headingId": hId}

    
    if print_header:
        headers = oldHeaders
        currentParentTypes = oldCurrentParentTypes
        hId = oldHId
    return text


def create_docs_service():
    """Uses the discovery API to create a service object."""
    return create_service.Create_Service("client_secret.json", "docs", "v1", SCOPES)

def parse_doc(document_id, service):
    """Uses the Docs API to parse the document into paragraphs with links and prefixes."""

    doc = service.documents().get(documentId=document_id).execute()
    global contentTree
    global currentParentTypes
    global headers
    global hId
    hId = ""
    contentTree = dict()
    currentParentTypes = []
    headers = []
    doc_content = doc.get('body').get('content')
    sanatize(read_structural_elements(doc_content))

    sections = []
    for k, v in contentTree.items():
        link = "https://docs.google.com/document/d/" + document_id + "/edit#heading=" + k
        sections.append({"headers": v["headers"], "text": v["text"], "link": link})
    return sections

