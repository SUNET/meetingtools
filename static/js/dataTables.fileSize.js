/**
 * Created by lundberg on 4/2/14.
 */

// http://datatables.net/plug-ins/type-detection
// http://datatables.net/plug-ins/sorting

jQuery.fn.dataTableExt.aTypes.unshift(
    function ( sData ) {
        var sValidChars = "0123456789";
        var Char;

        /* Check the numeric part */
        for ( i=0 ; i<(sData.length - 3) ; i++ )
        {
            Char = sData.charAt(i);
            if (sValidChars.indexOf(Char) == -1)
            {
                return null;
            }
        }

        /* Check for size unit B, KB, MB or GB */
        if (sData.substring(sData.length - 2, sData.length) == "B"
            || sData.substring(sData.length - 2, sData.length) == "KB"
            || sData.substring(sData.length - 2, sData.length) == "MB"
            || sData.substring(sData.length - 2, sData.length) == "GB" )
        {
            return 'file-size';
        }
        return null;
    }
);
jQuery.extend( jQuery.fn.dataTableExt.oSort, {
    "file-size-pre": function ( a ) {
        var x = a.substring(0,a.length - 2);

        var x_unit = (a.substring(a.length - 2, a.length) == "MB" ?
            1000 : (a.substring(a.length - 2, a.length) == "GB" ? 1000000 : 1));

        return parseInt( x * x_unit, 10 );
    },

    "file-size-asc": function ( a, b ) {
        return ((a < b) ? -1 : ((a > b) ? 1 : 0));
    },

    "file-size-desc": function ( a, b ) {
        return ((a < b) ? 1 : ((a > b) ? -1 : 0));
    }
} );
