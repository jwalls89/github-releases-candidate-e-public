"""Invoke task collections."""

from invoke import Collection

from tasks import release

ns = Collection()
ns.add_collection(Collection.from_module(release), name="release")
