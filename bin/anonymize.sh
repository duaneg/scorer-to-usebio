#!/bin/bash

# Make some attempt to anonymize sample scorer data. Replaces player names and
# NZ Bridge numbers with generated values.

xsltproc - "$@" <<EOF
<?xml version="1.0"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:variable name="counter" select="0"/>
  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>
  <xsl:template match="@player_name_1">
    <xsl:attribute name="player_name_1">
      <xsl:value-of select="concat('p', count(preceding::pair), '_1')" />
    </xsl:attribute>
  </xsl:template>
  <xsl:template match="@player_name_2">
    <xsl:attribute name="player_name_2">
      <xsl:value-of select="concat('p', count(preceding::pair), '_2')" />
    </xsl:attribute>
  </xsl:template>
  <xsl:template match="@nzb_no_1">
    <xsl:attribute name="nzb_no_1">
      <xsl:value-of select="count(preceding::pair) * 2" />
    </xsl:attribute>
  </xsl:template>
  <xsl:template match="@nzb_no_2">
    <xsl:attribute name="nzb_no_2">
      <xsl:value-of select="count(preceding::pair) * 2 + 1" />
    </xsl:attribute>
  </xsl:template>
</xsl:stylesheet>
EOF
