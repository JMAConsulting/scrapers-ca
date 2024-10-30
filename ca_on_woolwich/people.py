import re
from collections import defaultdict

from utils import CanadianPerson as Person
from utils import CanadianScraper

COUNCIL_PAGE = "https://www.woolwich.ca/learn-about/council/"


class WoolwichPersonScraper(CanadianScraper):
    def scrape(self):
        seat_numbers = defaultdict(int)
        page = self.lxmlize(COUNCIL_PAGE)

        councillors = page.xpath('//div[@class="info repeatable-content collapse  "]')
        assert len(councillors), "No councillors found"
        for councillor in councillors[1:]:
            info = councillor.xpath('.//div[@class="text"]/p/text()') + councillor.xpath('.//div[@class="text"]/p/a/text()')
            name = info[-1].split("Email ")[-1]

            if "Councillor" in info[0]:
                role = "Councillor"
                area = re.search(r"Ward \d", info[0])
                if not area:
                    district = "Woolwich"
                else:
                    seat_numbers[area] += 1
                    district = area.group(0) + f" (seat {seat_numbers[area]})"
            else:
                role = "Mayor"

            office = re.search(r"(?<=Office: )\d{3}-\d{3}-\d{4}", info[1] if "Councillor" in info[0] else info[0]).group(0)
            voice = (
                re.search(r"(?<=Toll Free: )(1-)?\d{3}-\d{3}-\d{4}( extension \d{4})?", info[2] if "Councillor" in info[0] else info[3])
                .group(0)
                .replace("extension", "x")
            )

            p = Person(primary_org="legislature", name=name, district=district, role=role)
            p.add_source(COUNCIL_PAGE)
            p.add_contact("voice", office, "office")
            p.add_contact("voice", voice, "legislature")

            yield p
