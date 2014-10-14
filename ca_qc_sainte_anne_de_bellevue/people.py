from __future__ import unicode_literals
from pupa.scrape import Scraper

import re

from utils import lxmlize, CanadianPerson as Person

COUNCIL_PAGE = 'http://www.ville.sainte-anne-de-bellevue.qc.ca/Democratie.aspx'


class SainteAnneDeBellevuePersonScraper(Scraper):

  def scrape(self):
    page = lxmlize(COUNCIL_PAGE)

    councillors = page.xpath('//div[@id="content"]//tr')

    for i, councillor in enumerate(councillors):
      if 'Maire' in councillor.text_content():
        name = councillor.xpath('./td')[1].text_content()
        district = 'Sainte-Anne-de-Bellevue'
        role = 'Maire'
      else:
        name = councillor.xpath('./td')[1].text_content()
        district = 'District ' + re.findall(r'\d', councillor.xpath('./td')[0].text_content())[0]
        role = 'Conseiller'

      p = Person(name=name, post_id=district, role=role)
      p.add_source(COUNCIL_PAGE)

      email = councillor.xpath('.//a')
      if email:
        email = email[0].attrib['href'].replace('mailto:', '')
        p.add_contact('email', email, None)
      yield p
