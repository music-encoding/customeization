<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:math="http://www.w3.org/2005/xpath-functions/math"
    xmlns:xd="http://www.oxygenxml.com/ns/doc/xsl"
    xmlns="http://www.w3.org/1999/xhtml"
    xpath-default-namespace="http://www.w3.org/1999/xhtml"
    exclude-result-prefixes="xs math xd"
    version="2.0">
    <xd:doc scope="stylesheet">
        <xd:desc>
            <xd:p><xd:b>Created on:</xd:b> Mar 24, 2015</xd:p>
            <xd:p><xd:b>Author:</xd:b> Johannes Kepper</xd:p>
            <xd:p></xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:output method="xml" encoding="UTF-8"/>
    
    <xsl:param name="version" select="'2.1.1'" as="xs:string"/>
    
    <xsl:variable name="elements" select="//h3[starts-with(text(),'&lt;')]/parent::node()" as="node()*"/>
    <xsl:variable name="elementIDs" select="$elements/replace(replace(./h3/text(),'&lt;',''),'&gt;','')" as="xs:string*"/>
    <xsl:variable name="linkTargets" select="//@id/parent::node()" as="node()*"/>
    
    <xsl:variable name="targets" select="distinct-values(//@id, $elementIDs)" as="xs:string*"/>
    
    <xsl:variable name="chapterIDs" select="//div[@class eq 'tei_front']/section[contains(@class,'included')]/@id | //div[@class eq 'tei_body']/section/@id"/>
    
    <xsl:template match="/">
        <xsl:apply-templates/>
    </xsl:template>
    
    <!-- fixing css references -->
    <xsl:template match="link[@rel = 'stylesheet' and ends-with(@href,'tei.css')]">
        <link rel="stylesheet" media="print" type="text/css" href="css/mei.css"/>
    </xsl:template>
    <xsl:template match="link[@rel = 'stylesheet' and ends-with(@href,'tei-print.css')]">
        <link rel="stylesheet" media="print" type="text/css" href="css/mei-print.css"/>
    </xsl:template>
    
    <xsl:template match="div[@class = 'titlePage']/text()[matches(.,'[a-zA-Z]+')]">
        <div class="beginPages">
            <xsl:apply-templates select="following-sibling::node()" mode="include"/>
        </div>
    </xsl:template>
    
    <xsl:template match="*[parent::div[@class = 'titlePage'] and preceding-sibling::text()[matches(.,'[a-zA-Z]+')]]"/>
    
    <xsl:template match="*[@class = 'docImprint' and parent::div[@class = 'titlePage'] and preceding-sibling::text()[matches(.,'[a-zA-Z]+')]]" mode="include">
        <xsl:copy>
            <xsl:apply-templates select="@*"/>
            <xsl:apply-templates select="preceding-sibling::text()[matches(.,'[a-zA-Z]+')]" mode="include"/>
            <br />
            <br />
            <xsl:apply-templates select="child::node()"/>
        </xsl:copy>
    </xsl:template>
    
    <!-- preparing preface pages -->
    <xsl:template match="div[@class = 'teidiv0' and preceding-sibling::div[@class = 'titlePage']]/@class">
        <xsl:attribute name="class" select="'teidiv0 alsoBegin'"/>
    </xsl:template>
    
    <!-- reset page counter -->
    <xsl:template match="div[@class = 'div1' and not(preceding::div[@class='div1'])]/@class">
        <xsl:message>Starting regular page numbering</xsl:message>
        <xsl:attribute name="class" select="'div1 regularPage'"/>
    </xsl:template>
    
    <xsl:template match="div[contains(@class,'stdfooter')]"/>
    
    <xsl:template match="span[@class='gi']">
        <xsl:choose>
            <xsl:when test="starts-with(text(),'&lt;') and ends-with(text(),'&gt;')">
                <xsl:variable name="newText" select="replace(replace(text(),'&lt;',''),'&gt;','')"/>
                <a href="#{$newText}"><xsl:value-of select="$newText"/></a>
            </xsl:when>
            <xsl:otherwise>
                <xsl:copy>
                    <xsl:apply-templates select="node() | @*"/>
                </xsl:copy>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <!-- remove wrong reference to TEI namespace from element title -->
    <xsl:template match="h3[@class='oddSpec status_stable' and contains(text(),'&gt;') and contains(text(),'&lt;')]">
        <xsl:copy>
            <xsl:value-of select="concat(substring-before(text(),'&gt;'),'&gt;')"/>
        </xsl:copy>
    </xsl:template>
    
    <!-- remove namespace row from table -->
    <xsl:template match="tr[parent::table[@class='wovenodd'] and .//span[text() = 'Namespace']]"/>
    
    <!-- remove unwanted text in appendix chapters -->
    <xsl:template match="h2[starts-with(text(),'Schema mei: ')]">
        <xsl:copy>
            <xsl:apply-templates select="@*"/>
            <xsl:variable name="newText" select="substring-after(text(),'Schema mei: ')"/>
            <xsl:value-of select="if(contains($newText,'Macros')) then('Datatypes and Macros') else($newText)"/>
        </xsl:copy>
    </xsl:template>
    
    <!-- rearranging attribute lists -->
    <xsl:template match="td[@class='wovenodd-col2' and preceding-sibling::td[1][contains(./span/text(),'Attributes')]]">
        <xsl:copy>
            <xsl:apply-templates select="table[@class = 'attList'] | @*"/>
            <xsl:apply-templates select="span[@class='attribute']" mode="reorderAtts">
                <xsl:sort select="substring(text(),2,1)" data-type="text"/>
            </xsl:apply-templates>
        </xsl:copy>
    </xsl:template>
    <xsl:template match="span[@class='attribute']" mode="reorderAtts">
        <div class="attributeDef">
            <xsl:copy>
                <xsl:apply-templates select="node() | @*"/>
            </xsl:copy>
            <xsl:variable name="classes" select="preceding-sibling::a[@class='link_odd'][1]"/>
            <span class="attributeClasses">
                <xsl:apply-templates select="reverse($classes)"/>
            </span>
        </div>
    </xsl:template>
    
    <!-- making links from attribute / model classes to elements functional -->
    <xsl:template match="span[@class='showmembers1']">
        <xsl:apply-templates select="node()"/>
    </xsl:template>
    <xsl:template match="@class[string(.) = 'link_odd_elementSpec']"/>
    
    <!-- wrapping solidus character into a span -->
    <xsl:template match="div[@id = 'harmonyFigbass']//text()">
        <xsl:choose>
            <xsl:when test="contains(.,'⃥')">
                <xsl:value-of select="substring-before(.,'⃥')"/><span class="solidus">⃥</span><xsl:value-of select="substring-after(.,'⃥')"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="."/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <!-- adding ids to elements -->
    <xsl:template match="div[@class eq 'tei_back']/section/div[starts-with(./h3/text(),'&lt;')]">
        <xsl:copy>
            <xsl:variable name="id" select="replace(replace(./h3/text(),'&lt;',''),'&gt;','')" as="xs:string"/>
            <xsl:attribute name="id" select="$id"/>
            <xsl:apply-templates select="node() | (@* except @id)"/>
        </xsl:copy>
    </xsl:template>
    
    <!-- adding classes to links to elements -->
    <xsl:template match="a[replace(@href,'#','') = $elementIDs]">
        <xsl:copy>
            <xsl:attribute name="class" select="concat('link_odd_elementSpec', if(@class and @class != 'link_odd_elementSpec') then(concat(' ', replace(@class,'link_odd_elementSpec',''))) else(''))"/>
            <xsl:apply-templates select="node() | (@* except @class)"/>
        </xsl:copy>
    </xsl:template>
    
    <xsl:template match="div['pre' = tokenize(@class,' ')]">
        <xsl:copy>
            <xsl:apply-templates select="@*"/>
            <xsl:apply-templates select="node()" mode="indent"/>
        </xsl:copy>
    </xsl:template>
    
    <xsl:template match="span[@class = 'element']" mode="indent">
        <xsl:copy>
            
            <xsl:variable name="pre.elems" select="preceding-sibling::span[@class='element' and not(ends-with(./text()[last()],'/&gt;')) and not(starts-with(./text()[1],'&lt;/'))]" as="node()*"/>
            <xsl:variable name="pre.closed" select="preceding-sibling::span[@class='element' and starts-with(./text()[1],'&lt;/')]" as="node()*"/>
            <xsl:variable name="self.offset" select="if(starts-with(./text()[1],'&lt;/')) then(-1) else(0)" as="xs:integer"/>
            
            <!-- debug -->
            <!--<xsl:if test="ancestor::div[@id = 'index.xml-egXML-d39e5831']">
                <xsl:message select="'calc for ' || replace(replace(./text()[1],'&gt;',''),'&lt;','') || ': ' || count($pre.elems) || ' - ' || count($pre.closed) || ' + 1 + ' || $self.offset || ' = ' || (count($pre.elems) - count($pre.closed) + 1 + $self.offset)"/>
            </xsl:if>-->
            
            <xsl:variable name="level" select="count($pre.elems) - count($pre.closed) + 1 + $self.offset" as="xs:integer"/>
            <xsl:attribute name="data-indentation" select="$level"/>
            <xsl:apply-templates select="node() | @*" mode="#current"/>
        </xsl:copy>
        
        <xsl:variable name="hasText" select="following-sibling::node()[1]/self::text() and matches(following-sibling::text()[1],'[\w]+')" as="xs:boolean"/>
        <xsl:variable name="nextCloses" select="starts-with(following-sibling::span[@class='element'][1]/text()[1],'&lt;/')" as="xs:boolean"/>
        
        <xsl:if test="following-sibling::span[@class='element'] and not($hasText and $nextCloses)">
            <br xmlns="http://www.w3.org/1999/xhtml"/>
        </xsl:if>
    </xsl:template>
    
    <xsl:template match="br[ancestor::span[@class='element']]" mode="indent"/>
    
    <xsl:template match="text()" mode="indent" priority="1">
        <xsl:value-of select="normalize-space(.)"/>
    </xsl:template>
    
    <xsl:template match="node() | @*" mode="#all">
        <xsl:copy>
            <xsl:apply-templates select="node() | @*" mode="#current"/>
        </xsl:copy>
    </xsl:template>
    
    
    
</xsl:stylesheet>