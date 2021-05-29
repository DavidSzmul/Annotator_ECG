clear; close all;
files = dir('*.mat');
File_name = {files.name};

%%% Parameters to add
Fs = 250;
nb_parts = 1;
Factor_mV = 1000;
for i=1:length(File_name)
    save(File_name{i},'Fs','nb_parts','Factor_mV','-append');
    disp(['Frequency added in ',File_name{i}]);
end