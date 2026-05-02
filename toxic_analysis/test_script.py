import sys
sys.path.insert(0, '.')
from collect.youtube_scraper import thu_thap_youtube
df = thu_thap_youtube(['Akj12zQniWw'], output_path='./data/collected/test_youtube.csv')
print('So binh luan load duoc:', len(df))
