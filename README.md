DISCO
=====

(Docker Inspired Slice of COmpute Discovery Service)

Use various service discovery backends and handlers to configure a container at
runtime. Disco will poll/watch various configured sources, validate the
configuration data according to various schema and then match various rules to
dispatch handlers within the container. If all the rules have been completed
successfully disco will exit by exec'ing the containers primary command.

Sources
=======

Sources are various systems for service discovery, consul and etcd for example.
These provide data which is then validated according to schemas.

Consul
------

TBD

Etcd
----

TBD

Flat Files
----------

Used for testing flat files are just YAML blobs read from the container.
Because you could bind mount these in this isn't a completely useless thing to
do.

Rules
=====

You may include any number of .rules files in your container. These files
should be YAML formatted with the following structure:

    rules:
        - when: <interface>
          do: <handler>

'When' targets an interface for which there should be a matching schema. The
when rule triggers by default when all the data from composed sources include a
key under which enough valid data exists to satisfy the schema.

When also supports additional triggering rules in the format:
    - when: any:x,y,z
    - when: all:x,y,z
    - when: x,y,z

'all' is the default operation for comma delimited interface names (thus the
last two examples are identical). All means all interfaces must validate before
the rule can trigger.

'any' means at least one of the listed interfaces must validate with proper data.

'do' should specify a handler. See the handlers section for calling conventions.

Handlers
========
Handlers are passed a JSON serialized bag of data containing all the matched
(validate) interfaces from their 'when' trigger. This is written to STDIN of the 
handler process. The handler then only need exit normally (0) for the rule to
succeed. If the handler fails a number of times (see disco.fail_limit) we assume
the handler is broken and terminate. We take this approach because we have some
assurances that the data is valid based on the schema and rules.



Configuration
=============

Disco is configured with the DISCO_CFG environment variable and can take a
number of flags this way. DISCO_CFG is a ':' delimited set of key/value pairs
where the keys are namespaces via a '.'. Subsystems (disco and the various
backends) then have values in their namespace available to them at runtime.


  disco.path: (str) directory in container to use for schema, rules and
  handlers

  disco.interval: (int:1) time in seconds to sleep between reading various
  service backends or dispatching handlers

  disco.fail_limit: (int:5) the number of times a handler can be invoked with
  validated data before we assume it won't exit successfully


  <source>.<key>: a mapping of all keys under source will be available to the
  source 


  Flat
  ----
  flat.file: (path) SCnfigure the flat file source with a configuration file in YAML



Examples
========

For now, examples assume you've installed tox and can run from inside its
testing environment. 

$ tox
$ . .tox/py35/bin/activate
$ env DISCO_CFG=flat.file=tests/mysql.yaml:disco.path=tests disco echo "doit"



Debugging
=========

If disco isn't working as expected you might try calling it as 'disco -l DEBUG'
which will show more detailed operations including handler failure.
