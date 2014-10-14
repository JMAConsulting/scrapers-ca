from __future__ import unicode_literals
from pupa.scrape import Scraper

import re

from utils import lxmlize, CanadianPerson as Person

COUNCIL_PAGE = 'http://www.city.kawarthalakes.on.ca/city-hall/mayor-council/members-of-council'


class KawarthaLakesPersonScraper(Scraper):

  def scrape(self):

    page = lxmlize(COUNCIL_PAGE)

    councillors = page.xpath('//p[@class="WSIndent"]/a')
    for councillor in councillors:
      district = re.findall(r'(Ward [0-9]{1,2})', councillor.text_content())
      if district:
        district = district[0]
        name = councillor.text_content().replace(district, '').strip()
        role = 'Councillor'
      else:
        district = 'Kawartha Lakes'
        name = councillor.text_content().replace('Mayor', '').strip()
        role = 'Mayor'

      url = councillor.attrib['href']
      page = lxmlize(url)
      email = page.xpath('//a[contains(@href, "mailto:")]/@href')[0].rsplit(':', 1)[1].strip()
      image = page.xpath('//img[@class="image-right"]/@src')[0]

      p = Person(name=name, post_id=district, role=role)
      p.add_source(COUNCIL_PAGE)
      p.add_source(url)
      p.add_contact('email', email, None)
      p.image = image
      yield p
