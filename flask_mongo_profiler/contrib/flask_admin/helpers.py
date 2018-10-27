# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import re

import bson
import mongoengine

from ...constants import RE_OBJECTID


def get_list_url_filtered_by_field_value(view, model, name, reverse=False):
    """Get the URL if a filter of model[name] value was appended.

    This allows programatically adding filters. This is used in the specialized case
    of filtering deeper into a list by a field's value.

    For instance, since there can be multiple assignments in a list of handins. The
    assignment column can have a URL generated by get_filter_url to filter the handins
    to show only ones for that assignment.

    Parameters
    ----------
    view : View instance
    model : document (model instance, not the class itself)
    name : field name
    reverse : bool
        Whether to *remove* an applied filter from url

    Returns
    -------
    string : URL of current list args + filtering on field value
    """

    view_args = view._get_list_extra_args()

    def create_filter_arg(field_name, value):
        i, flt = next(
            (
                v
                for k, v in view._filter_args.items()
                if k == '{}_equals'.format(field_name)
            ),
            None,
        )
        return (i, flt.name, value)

    new_filter = create_filter_arg(name, model[name])
    filters = view_args.filters

    if new_filter in view_args.filters:  # Filter already applied
        if not reverse:
            return None
        else:  # Remove filter
            filters.remove(new_filter)

    if not reverse:  # Add Filter
        filters.append(new_filter)

    # Example of an activated filter: (u'view_args.filters', [(7, u'Path', u'course')])
    return view._get_list_url(
        view_args.clone(filters=filters, page=0)  # Reset page to 0
    )


def search_relative_field(model_class, fields, term):
    """Searches a ReferenceField's fields, returning ID's to be used in __in

    There is no JOIN, so no Assignment.objects.filter(course__title='My Course'). To
    get around this, we return a list of ID's.

    Since this is an internal tool, we allow multiple fields to AND/OR group.
    """
    offset = 0
    limit = 500
    query = model_class.objects

    criteria = None

    # If an ObjectId pattern, see if we can get an instant lookup.
    if re.match(RE_OBJECTID, term):
        q = query.filter(id=bson.ObjectId(term)).only('id')
        if q.count() == 1:  # Note: .get doesn't work, they need a QuerySet
            return q

    for field in fields:
        flt = {u'%s__icontains' % field: term}

        if not criteria:
            criteria = mongoengine.Q(**flt)
        else:
            criteria |= mongoengine.Q(**flt)

    query = query.filter(criteria)

    if offset:
        query = query.skip(offset)

    return query.limit(limit).only('id').all()
