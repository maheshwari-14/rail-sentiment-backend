from owlready2 import *

# Create a new empty ontology
onto = get_ontology("http://example.org/railway-sentiment.owl")

with onto:
    # 1. Create the Core Classes
    class Train(Thing): 
        pass
    class Sentiment(Thing): 
        pass

    # 2. Create the Data Properties (Categories)
    class hasCleanliness(DataProperty):
        domain    = [Train]
        range     = [int]

    class hasStaffBehaviour(DataProperty):
        domain    = [Train]
        range     = [int]

    class hasPunctuality(DataProperty):
        domain    = [Train]
        range     = [int]

    class hasSecurity(DataProperty):
        domain    = [Train]
        range     = [int]

    class hasTimeliness(DataProperty):
        domain    = [Train]
        range     = [int]

    # 3. Create the final Sentiment output property
    class hasSentiment(DataProperty):
        domain    = [Train]
        range     = [int]

# Save it to the current folder
onto.save("railway-sentiment.owl")
print("✅ railway-sentiment.owl has been successfully generated!")