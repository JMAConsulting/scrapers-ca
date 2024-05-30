# coding: utf-8
from utils import CanadianPerson as Person
from utils import CanadianScraper

COUNCIL_PAGE = "https://www.ville.levis.qc.ca/la-ville/conseil-municipal/elus/"


class LevisPersonScraper(CanadianScraper):
    def scrape(self):
        page = self.lxmlize(COUNCIL_PAGE)

        councillors = page.xpath('//div[@class="drawers"]//div[@class="dropdown"]')
        assert len(councillors), "No councillors found"
        for person in councillors:
            position, name = person.xpath("./h3/text()")[0].replace("–", "-").split(" - ")
            if "," in position:
                role, district = position.title().split(", ")[0].split(" ", 1)
            else:
                role = "Maire"
                district = "Lévis"

            if role == "Conseillère":
                role = "Conseiller"

            photo_url = person.xpath(".//img/@src")[0]
            email = self.get_email(person)

            p = Person(primary_org="legislature", name=name, district=district, role=role)
            p.add_source(COUNCIL_PAGE)
            p.image = photo_url
            p.add_contact("email", email)
            yield p
