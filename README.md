# futuresense
## Predicting Blood Glucose Levels

### Business Understanding
Can you specify a clear research question, use case or business problem?
I would like to use Continuous Glucose Monitoring (CGM) data to a) be more predictive of extreme high/low glucose events; b) create a more personalized model for basal/bolus insulin rates; and c) help provide better overall health outcomes for people with Type I diabetes.

### Data Understanding
Can you specify potential data sources and includes a plan for obtaining data ?
Dexcom (the manufacturer of the CGM I use) recently released an API for interacting with CGM data, which includes some “training” data sets. I also intend to leverage the Nightscout community (started by parents of children with Type I diabetes to get their CGM data into the cloud for greater accessibility) to get more real world data.

### Data Preparation
Can you include a conceptual explanation of the proposed data pipeline to transform raw data into an analytics base table (ABT) for modeling?
Dexcom offers “training” data for multiple users with 2 years’ worth of readings, and I could get more user data from the Nightscout community. For each user, there will be lots of missing data, readings with “low confidence” (per the CGM), and varying levels of available non-reading “event” data (eg, a user can record when they eat food, take insulin, exercise, etc), so I will have to come up with a weighted model based on data quality.

### Modeling
Can you specify one or more specific statistical or machine learning techniques as candidates for evaluation?
I will use time-series analysis to build the model and identify daily seasonal trends, in addition to patterns of combinations of events (eg, ate X grams of carbohydrates and took Y units of insulin, resulting in subsequent increase in glucose levels of Z mg/dL).

### Evaluation
Can you devise a plan for evaluating model performance?
Cross-validation will be used for initial evaluation of the model, but once the model is functional, user feedback will be key to improving accuracy. 

### Deployment
Can you specify a minimal viable product (MVP) for presentation and deployment?
MVP will be a program that can predict high or low glucose events with a high probability, better than existing trendline predictions. The next step would be to model basal and bolus insulin formulas.
