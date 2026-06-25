%----------------------------------------------------
function [N, Mean, Std, Skewness, Kurtosis,q_25,q_50,q_75] = get_stats(s)
        N = numel(s(:));
        Mean = mean(s(:));
        Std = std(s(:));
        Skewness = skewness(s(:));
        Kurtosis = kurtosis(s(:));
        z = quantile(s(:),[.25 .50 .75]);
        q_25 = z(1);
        q_50 = z(2);
        q_75 = z(3);
end