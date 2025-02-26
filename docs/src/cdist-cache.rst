Local cache overview
====================

Description
-----------
While executing, skonfig stores data to local cache. Currently this feature is
one way only. That means that skonfig does not use stored data for future runs.
Anyway, those data can be used for debugging skonfig, debugging types and
debugging after host configuration fails.

Local cache is saved under $HOME/.skonfig/dump directory, one directory entry
for each host. Subdirectory path is specified by the
:strong:`cache_path_pattern` configuration option.

For more info on cache path pattern see :strong:`CACHE PATH PATTERN FORMAT`
section.


Cache overview
--------------
As noted above each configured host has got its subdirectory in local cache.
Entries in host's cache directory are as follows.

bin
  directory with cdist-type emulators

conf
  dynamically determined conf directory, union of all specified
  conf directories

explorer
  directory containing global explorer named files containing explorer output
  after running on target host

messages
  file containing messages

object
  directory containing subdirectory for each object

object_marker
  object marker for this particular configuration run

stderr
  directory containing init manifest and remote stderr stream output

stdout
  directory containing init manifest and remote stdout stream output

target_host
  file containing target host of this configuration run, as specified when
  running skonfig(1).

typeorder
  file containing types in order of execution.


Object cache overview
~~~~~~~~~~~~~~~~~~~~~
Each object under :strong:`object` directory has its own structure.

autorequire
    file containing a list of object auto requirements

children
    file containing a list of object children, i.e. objects of types that this
    type reuses (along with 'parents' it is used for maintaining parent-child
    relationship graph)

code-local
    code generated from gencode-local, present only if something is
    generated

code-remote
    code generated from gencode-remote, present only if something is
    generated

explorer
    directory containing type explorer named files containing explorer output
    after running on target host

files
    directory with object files created during type execution

parameter
    directory containing type parameter named files containing parameter
    values

parents
    file containing a list of object parents, i.e. objects of types that reuse
    this type (along with 'children' it is used for maintaining parent-child
    relationship graph); objects without parents are objects specified in init
    manifest

require
    file containing a list of object requirements

source
    this type's source (init manifest)

state
    this type execution state ('done' when finished)

stderr
  directory containing type's manifest, gencode-* and code-* stderr stream
  outputs

stdin
    this type stdin content

stdout
  directory containing type's manifest, gencode-* and code-* stdout stream
  outputs.


CACHE PATH PATTERN FORMAT
-------------------------
Cache path pattern specifies path for a cache directory subdirectory.
In the path, ``%N`` will be substituted by the target host, ``%h`` will
be substituted by the calculated host directory, ``%P`` will be substituted
by the current process id. All format codes that
Python's ``datetime.strftime()`` function supports, except
``%h``, are supported. These date/time directives format cdist config/install
start time.

If empty pattern is specified then default calculated host directory is used.

Calculated host directory is a hash of a host cdist operates on.

Resulting path is used to specify cache path subdirectory under which
current host cache data are saved.
