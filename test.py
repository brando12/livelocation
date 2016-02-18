
from nltk.corpus import stopwords


s=set(stopwords.words('english'))

txt="This crab place has the best view i have ever seen"
print filter(lambda w: not w in s,txt.split())
