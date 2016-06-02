An example of the structure of a DISCO layer

This can include more than one schema. For each 'when' rule the name should
resolve to a schema. Regardless of which source we pull configuration
information from the data provided should ultimately match the schema and
validate. When this is successful the rule will trigger. When all the rules
have triggered DISCO will exit and execute the containers command.
