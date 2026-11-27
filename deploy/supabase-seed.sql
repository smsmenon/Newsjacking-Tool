insert into sources (name, category, url, rss_url, access_method, trust_tier)
values
  ('Industry Week', 'Manufacturing', 'https://www.industryweek.com/', 'https://www.industryweek.com/rss.xml', 'rss', 2),
  ('Manufacturing Dive', 'Manufacturing', 'https://www.manufacturingdive.com/', 'https://www.manufacturingdive.com/feeds/news/', 'rss', 2),
  ('Supply Chain Dive', 'Supply Chain', 'https://www.supplychaindive.com/', 'https://www.supplychaindive.com/feeds/news/', 'rss', 2),
  ('Gartner', 'Analyst Firms', 'https://www.gartner.com/', null, 'licensed_api_or_manual', 1),
  ('IDC', 'Analyst Firms', 'https://www.idc.com/', null, 'licensed_api_or_manual', 1),
  ('Forrester', 'Analyst Firms', 'https://www.forrester.com/', null, 'licensed_api_or_manual', 1),
  ('McKinsey', 'Consulting Firms', 'https://www.mckinsey.com/', null, 'rss_or_scrape', 1),
  ('BCG', 'Consulting Firms', 'https://www.bcg.com/', null, 'rss_or_scrape', 1),
  ('VentureBeat', 'Technology & AI', 'https://venturebeat.com/', 'https://venturebeat.com/feed/', 'rss', 2),
  ('InformationWeek', 'Technology & AI', 'https://www.informationweek.com/', 'https://www.informationweek.com/rss.xml', 'rss', 2)
on conflict (name) do nothing;

