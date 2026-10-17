Option Explicit

Dim showWindow, needsStart, shell, http, i
showWindow = False
If WScript.Arguments.Count > 0 Then
    If LCase(WScript.Arguments(0)) = "show" Then
        showWindow = True
    End If
End If

Set shell = CreateObject("WScript.Shell")
needsStart = True

On Error Resume Next
Set http = CreateObject("MSXML2.XMLHTTP")
http.Open "GET", "http://127.0.0.1:8787/api/show", False
http.Send
If Err.Number = 0 And http.Status = 200 Then
    needsStart = False
End If
Err.Clear
On Error GoTo 0

If needsStart Then
    shell.Run "schtasks /run /tn ""Synpu""", 0, False
    If showWindow Then
        For i = 1 To 30
            WScript.Sleep 500
            On Error Resume Next
            http.Open "GET", "http://127.0.0.1:8787/api/show", False
            http.Send
            If Err.Number = 0 And http.Status = 200 Then
                Exit For
            End If
            Err.Clear
            On Error GoTo 0
        Next
    End If
End If
