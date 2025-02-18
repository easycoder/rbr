URL_RFC_3986 = {" ": "%20", "'": "%27", "\"": "%22"}

def encode(b):
    if type(b)==bytes:
        b = b.decode(encoding="utf-8") #byte can't insert many utf8 charaters
    result = bytearray() #bytearray: rw, bytes: read-only
    for i in b:
        if i in URL_RFC_3986:
            for j in URL_RFC_3986[i]:
                result.append(ord(j))
            continue
        i = bytes(i, "utf-8")
        if len(i)==1:
            result.append(ord(i))
        else:
            for c in i:
                c = hex(c)[2:].upper()
                result.append(ord("%"))
                result.append(ord(c[0:1]))
                result.append(ord(c[1:2]))
    result = result.decode("ascii")
    return result
