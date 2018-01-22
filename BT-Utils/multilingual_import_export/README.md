# Multilingual Import/Export

This module makes it possible to import and export records through csv with
different languages together.

This code will run when installing a module, so data can be uploaded through
csv in different languages.

## Export

In order to activate the export mechanism, go into your user preferences
(right-upper corner), and check the option "Use multilingual export".

Once set, whenever you export something through csv, it will add an additional
column called '.lang'. This column includes the code for the language used
in the current row.

## Import

In order to use the standard mechanism of import, don't include any column called
'.lang', so the standard functionality is used. 

When importing, lines are grouped by language, and imported together as if they
where part of a single csv without the '.lang' column, but, language will be set
through context, so translatable fields will be kept.