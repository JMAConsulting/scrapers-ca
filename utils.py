# coding: utf-8
from __future__ import unicode_literals

import csv
import re
from ftplib import FTP

import lxml.html
import requests
from pupa.scrape import Scraper, Jurisdiction, Membership, Organization, Person
from scrapelib import Scraper as Scrapelib
from six import StringIO, string_types, text_type
from six.moves.urllib.parse import urlparse

import patch

CONTACT_DETAIL_TYPE_MAP = {
  'Address': 'address',
  'bb': 'cell',
  'bus': 'voice',
  'Bus': 'voice',
  'Bus.': 'voice',
  'Business': 'voice',
  'Cell': 'cell',
  'Cell Phone': 'cell',
  'Email': 'email',
  'Fax': 'fax',
  'Home': 'voice',
  'Home Phone': 'voice',
  'Home Phone*': 'voice',
  'Office': 'voice',
  'ph': 'voice',
  'Phone': 'voice',
  'Res': 'voice',
  'Res/Bus': 'voice',
  'Residence': 'voice',
  'Téléphone (bureau)': 'voice',
  'Téléphone (cellulaire)': 'cell',
  'Téléphone (résidence)': 'voice',
  'Téléphone (résidence et bureau)': 'voice',
  'Voice Mail': 'voice',
  'Work': 'voice',
}
# In Newmarket, for example, there are both "Phone" and "Business" numbers.
CONTACT_DETAIL_NOTE_MAP = {
  'Address': 'legislature',
  'bb': 'legislature',
  'bus': 'office',
  'Bus': 'office',
  'Bus.': 'office',
  'Business': 'office',
  'Cell': 'legislature',
  'Cell Phone': 'legislature',
  'Email': None,
  'Fax': 'legislature',
  'Home': 'residence',
  'Home Phone': 'residence',
  'Home Phone*': 'residence',
  'ph': 'legislature',
  'Phone': 'legislature',
  'Office': 'legislature',
  'Res': 'residence',
  'Res/Bus': 'office',
  'Residence': 'residence',
  'Téléphone (bureau)': 'legislature',
  'Téléphone (cellulaire)': 'legislature',
  'Téléphone (résidence)': 'residence',
  'Téléphone (résidence et bureau)': 'legislature',
  'Voice Mail': 'legislature',
  'Work': 'legislature',
}


class CanadianJurisdiction(Jurisdiction):
  def __init__(self):
      super(CanadianJurisdiction, self).__init__()
      for module, name in (('people', 'Person')):
        class_name = self.__class__.__name__ + name + 'Scraper'
        self.scrapers[module] = getattr(__import__(self.__module__ + '.' + module, fromlist=[class_name]), class_name)

  def get_organizations(self):
    yield Organization(self.name, classification=self.classification)


class CanadianPerson(Person):

  def __init__(self, name, post_id, **kwargs):
    super(CanadianPerson, self).__init__(clean_name(name), clean_string(post_id), **kwargs)
    for k, v in kwargs.items():
      if isinstance(v, string_types):
        setattr(self, k, clean_string(v))

  def __setattr__(self, name, value):
    if name == 'gender':
      if value == 'M':
        value = 'male'
      elif value == 'F':
        value = 'female'
    super(CanadianPerson, self).__setattr__(name, value)

  def add_link(self, url, *, note=''):
      if url.startswith('www.'):
        url = 'http://%s' % url
      if re.match(r'\A@[A-Za-z]+\Z', url):
        url = 'https://twitter.com/%s' % url[1:]

      self.links.append({'note': note, 'url': url})

  def add_contact_detail(self, *, type, value, note=''):
    if type:
      type = clean_string(type)
    if note:
      note = clean_string(note)
    if type in CONTACT_DETAIL_TYPE_MAP:
      type = CONTACT_DETAIL_TYPE_MAP[type]
    if note in CONTACT_DETAIL_NOTE_MAP:
      note = CONTACT_DETAIL_NOTE_MAP[note]

    type = type.lower()

    if type in ('text', 'voice', 'fax', 'cell', 'video', 'pager'):
      value = clean_telephone_number(clean_string(value))
    elif type == 'address':
      value = clean_address(value)
    else:
      value = clean_string(value)

    self.contact_details.append({'type': type, 'value': value, 'note': note})


# Removes _is_legislator flag and _contact_details. Used by aggregations.
# @see https://github.com/opencivicdata/pupa/blob/master/pupa/scrape/helpers.py
class AggregationPerson(Person):
  __slots__ = ('post_id')

  def __init__(self, name, post_id, **kwargs):
    super(AggregationPerson, self).__init__(clean_name(name), **kwargs)
    self.post_id = clean_string(post_id)
    for k, v in kwargs.items():
      if isinstance(v, string_types):
        setattr(self, k, clean_string(v))

  def __setattr__(self, name, value):
    if name == 'gender':
      if value == 'M':
        value = 'male'
      elif value == 'F':
        value = 'female'
    super(AggregationPerson, self).__setattr__(name, value)


whitespace_re = re.compile(r'[^\S\n]+', flags=re.U)
honorific_prefix_re = re.compile(r'\A(?:Councillor|Dr|Hon|M|Mayor|Mme|Mr|Mrs|Ms|Miss)\.? ')
honorific_suffix_re = re.compile(r', Ph\.D\Z')

table = {
  ord('​'): ' ',  # zero-width space
  ord('’'): "'",
  ord('\xc2'): " ",  # non-breaking space if mixing ISO-8869-1 into UTF-8
}

# @see https://github.com/opencivicdata/ocd-division-ids/blob/master/identifiers/country-ca/ca_provinces_and_territories.csv
# @see https://github.com/opencivicdata/ocd-division-ids/blob/master/identifiers/country-ca/ca_provinces_and_territories-name_fr.csv
abbreviations = {
  'Newfoundland and Labrador': 'NL',
  'Prince Edward Island': 'PE',
  'Nova Scotia': 'NS',
  'New Brunswick': 'NB',
  'Québec': 'QC',
  'Ontario': 'ON',
  'Manitoba': 'MB',
  'Saskatchewan': 'SK',
  'Alberta': 'AB',
  'British Columbia': 'BC',
  'Yukon': 'YT',
  'Northwest Territories': 'NT',
  'Nunavut': 'NU',

  'PEI': 'PE',
}


def clean_string(s):
  return re.sub(r' *\n *', '\n', whitespace_re.sub(' ', text_type(s).translate(table)).strip())


def clean_name(s):
  return honorific_suffix_re.sub('', honorific_prefix_re.sub('', clean_string(s)))


def clean_telephone_number(s):
  """
  @see http://www.noslangues-ourlanguages.gc.ca/bien-well/fra-eng/typographie-typography/telephone-eng.html
  """

  splits = re.split(r'(?:/|x|ext[.:]?|poste)[\s-]?(?=\b|\d)', s, flags=re.IGNORECASE)
  digits = re.sub(r'\D', '', splits[0])

  if len(digits) == 10:
    digits = '1' + digits

  if len(digits) == 11 and digits[0] == '1' and len(splits) <= 2:
    digits = re.sub(r'\A(\d)(\d{3})(\d{3})(\d{4})\Z', r'\1-\2-\3-\4', digits)
    if len(splits) == 2:
      return '%s x%s' % (digits, splits[1])
    else:
      return digits
  else:
    return s


def clean_address(s):
  """
  Corrects the postal code, abbreviates the province or territory name, and
  formats the last line of the address.
  """

  # The letter "O" instead of the numeral "0" is a common mistake.
  s = re.sub(r'\b[A-Z][O0-9][A-Z]\s?[O0-9][A-Z][O0-9]\b', lambda x: x.group(0).replace('O', '0'), clean_string(s))
  for k, v in abbreviations.items():
      s = re.sub(r'[,\n ]+\(?' + k + r'\)?(?=(?:[,\n ]+Canada)?(?:[,\n ]+[A-Z][0-9][A-Z]\s?[0-9][A-Z][0-9])?\Z)', ' ' + v, s)
  return re.sub(r'[,\n ]+([A-Z]{2})(?:[,\n ]+Canada)?[,\n ]+([A-Z][0-9][A-Z])\s?([0-9][A-Z][0-9])\Z', r' \1  \2 \3', s)


def lxmlize(url, encoding='utf-8', user_agent=requests.utils.default_user_agent()):
  scraper = Scrapelib(requests_per_minute=0)
  scraper.user_agent = user_agent
  entry = scraper.urlopen(url)
  if encoding != 'utf-8' or not isinstance(entry, text_type):
    entry = entry.encode(encoding)
  page = lxml.html.fromstring(entry)
  meta = page.xpath('//meta[@http-equiv="refresh"]')
  if meta:
    _, url = meta[0].attrib['content'].split('=', 1)
    return lxmlize(url, encoding)
  else:
    page.make_links_absolute(url)
    return page


def csv_reader(url, header=False, encoding='utf-8', **kwargs):
  result = urlparse(url)
  if result.scheme == 'ftp':
    data = StringIO()
    ftp = FTP(result.hostname)
    ftp.login(result.username, result.password)
    ftp.retrbinary('RETR %s' % result.path, lambda block: data.write(text_type(block, encoding=encoding)))
    ftp.quit()
    data.seek(0)
  else:
    response = requests.get(url, **kwargs)
    response.encoding = encoding
    data = StringIO(response.text)
  if header:
    return csv.DictReader(data)
  else:
    return csv.reader(data)
