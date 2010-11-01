subdirs = \
lib_0\
lib_1\
lib_2\
lib_3\
lib_4\
lib_5\
lib_6\
lib_7\
lib_8\
lib_9\
lib_10\
lib_11\
lib_12\


all: $(subdirs)
	@for i in $(subdirs); do     $(MAKE) -C $$i all; done

clean:
	@for i in $(subdirs); do 	(cd $$i; $(MAKE) clean); done

depend:
	@for i in $(subdirs); do 	(cd $$i; $(MAKE) depend); done
