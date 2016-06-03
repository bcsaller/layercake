Layer-Cake
==========

Layer cake is a suite of tools for building, maintaining and configuring
containers. Container configuration is designed to be formalized around various
service discovery sources with schemas to validate incoming data for
correctness and rules to decide how to configure the container.

- disco Docker Inspired Slice of COmpute  - Discovery Service
- cake  Container Assemble Kit Extraordinaire

Use various service discovery sources and handlers to configure a container at
runtime. Disco will poll/watch various configured sources, validate the
configuration data according to various schema and then match various rules to
dispatch handlers within the container. If all the rules have been completed
successfully disco will exit by exec'ing the containers primary command.

Installation
============

Layercake depends on Python 3.5+


    pip3 install layercake


Sources
=======

Sources are various systems for service discovery, consul and etcd for example.
These provide data which is then validated according to schemas.

- Consul
- Etcd
- Flat Files

Sources will map backend data, usually at some fixed location in the remote
sources keyspace, to a map of YAML described data.


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

'any' means at least one of the listed interfaces must validate with proper
data.

'do' should specify a handler. See the handlers section for calling
conventions.

Handlers
========
Handlers are passed a JSON serialized bag of data containing all the matched
(validate) interfaces from their 'when' trigger. This is written to STDIN of
the handler process. The handler then only need exit normally (0) for the rule
to succeed. If the handler fails a number of times (see disco.fail_limit) we
assume the handler is broken and terminate. We take this approach because we
have some assurances that the data is valid based on the schema and rules.



Configuration
=============

Disco is configured with the DISCO_CFG environment variable and can take a
number of flags this way. DISCO_CFG is a '|' delimited set of key/value pairs
where the keys are namespaces via a '.'. Subsystems (disco and the various
backends) then have values in their namespace available to them at runtime.


      disco.path: (str) directory in container to use for schema, rules and
      handlers, path itself maybe ': delimited'

      disco.interval: (int:1) time in seconds to sleep between reading various
      service backends or dispatching handlers

      disco.fail_limit: (int:5) the number of times a handler can be invoked
      with validated data before we assume it won't exit successfully


      <source>.<key>: a mapping of all keys under source will be available to
      the source 


  Flat
  ----

      flat.file: (path) Configure the flat file source with a configuration file in YAML

  Consul
  ------

      consul.host: (str) http://addr:port

  Etcd
  ----

      etcd.host: (str) addr
      etcd.port: (int) port


Layers
======

Once you have an idea about how to configure your container it would be nice if
you could share and collaborate around the code required to do this. A layer,
in this context, are the rules, schema handlers and assets needed to configure
some aspect of a container.

For some container application the configuration is custom, for example, how to
configure yourself as a client of mysql, but then layer might still include
useful code you can use in your handler. It can always include verification
that your being passed the agreed upon data by setting up the proper schema and
rules.

Great applications are composed of many concerns, each of these can be modeled
in a layer and then the shared bits can be collaborated around so you can
always ensure a tasteful experience with your container.  

Along those lines we include a tool called 'cake', 'Container assembly kit
extraordinaire'. This can be used to resolve layers from a public, central
index and easily include them into your container at build time.

For example in a Dockerfile you might say

    RUN cake layer <layer-name>


Layers can be found at http://layer-cake.io

Layers should include a layer.yaml in their top directory with the following format:

layer.yaml
----------

    layer:
        name: layername
        author: Name
        repo: git repo
        repopath: <optional subpath under git repo to treat as the layer>


Cake
====

The 'cake' command has a 'build' directive that will take a cake.conf (yaml)
file and assist you in automatically updating a Dockerfile to include all the
proper directives to run disco. This will include pulling down any layers used
in the container, installing them and setting up the ENTRYPOINT to use disco.

cake.conf
---------

This simple YAML file should take the format 

    cake:
        layers: [ layername ]


Examples
========

For now, examples assume you've installed tox and can run from inside its
testing environment. 

    $ tox
    $ . .tox/py35/bin/activate
    $ env DISCO_CFG="flat.file=tests/mysql.yaml|disco.path=tests"" disco echo "doit"

This should load the mysql data from a flat file in the tests dir, which will
pass the schema, trigger a handler (also in the test dir) and then echo the
command

    $ curl -X PUT -d 'db.example.com' http://10.0.4.106:8500/v1/kv/mysql/host
    $ curl -X PUT -d 'test' http://10.0.4.106:8500/v1/kv/mysql/username
    $ curl -X PUT -d 'youshallnot' http://10.0.4.106:8500/v1/kv/mysql/password
    $ curl -X PUT -d 'test' http://10.0.4.106:8500/v1/kv/mysql/database
    $ env DISCO_CFG="consul.host=http://10.0.4.106:8500/|disco.path=tests|disco.interval=5" disco echo "doit"

After after changing IP address in the above command to your consul this will
pull the configuration information from consul like the previous example. With
the consul ui (http://10.0.4.106/ui in this example) you can do into the KV
store delete and add keys and see the changing behavior of disco.


Disco is intended to replace the CMD in your Dockerfile, this can be done by
prefixing the cmd with disco.

    CMD = disco <original cmd>


Debugging
=========

If disco isn't working as expected you might try calling it as 'disco -l DEBUG'
which will show more detailed operations including handler failure.
