#!/usr/bin/env python
import ROOT as r,sys,math,array,os
from optparse import OptionParser
from ROOT import std,RooDataHist
from array import array
import numpy as np
from scipy.stats import poisson, norm, kstest
from pvalue import *

fOutput="Output.root"
fHists=[]

def end():
    if __name__ == '__main__':
        rep = ''
        while not rep in [ 'q', 'Q','a',' ' ]:
            rep = raw_input( 'enter "q" to quit: ' )
            if 1 < len(rep):
                rep = rep[0]

def drawFrame(iX,iData,iBkg,iFuncs,iCat):
    lCan   = r.TCanvas("qcd_"+iCat,"qcd_"+iCat,800,600)
    leg = r.TLegend(0.55,0.63,0.86,0.87)
    lFrame = iX.frame()
    lFrame.SetTitle("")
    lFrame.GetXaxis().SetTitle("m_{jj} (GeV)")
    lFrame.GetYaxis().SetTitle("Events")
    #iBkg.plotOn(lFrame,r.RooFit.FillColor(r.TColor.GetColor(100, 192, 232)),r.RooFit.FillStyle(3008), r.RooFit.DrawOption("E3"), r.RooFit.LineColor(r.kBlue))
    iData.plotOn(lFrame)
    iColor=51
    lRange = len(iFuncs)
    for i0 in range(lRange):
        if i0 == 1:
            iFuncs[i0].plotOn(lFrame,r.RooFit.LineColor(r.kGreen+1))
        else:
            iFuncs[i0].plotOn(lFrame,r.RooFit.LineColor(iColor),r.RooFit.LineStyle(r.kDashed))
        iColor+=10
    leg.SetFillColor(0)
    lFrame.Draw()
    lTmpData  = r.TH1F("tmpData" ,"tmpData" ,1,0,10); lTmpData .SetMarkerStyle(r.kFullCircle); 
    lTmpBkg   = r.TH1F("tmpBkg"  ,"tmpBkg"  ,1,0,10); lTmpBkg  .SetFillStyle(3008); lTmpBkg.SetLineColor(r.kBlue); lTmpBkg.SetFillColor(r.TColor.GetColor(100, 192, 232));
    lTmpFunc1 = r.TH1F("tmpFunc1","tmpFunc1",1,0,10); lTmpFunc1.SetLineColor(51);                lTmpFunc1.SetLineWidth(2); lTmpFunc1.SetLineStyle(r.kDashed);
    lTmpFunc2 = r.TH1F("tmpFunc2","tmpFunc2",1,0,10); lTmpFunc2.SetLineColor(61);                lTmpFunc2.SetLineWidth(2); lTmpFunc2.SetLineStyle(r.kDashed);
    lTmpFunc3 = r.TH1F("tmpFunc3","tmpFunc3",1,0,10); lTmpFunc3.SetLineColor(r.kGreen+1);        lTmpFunc3.SetLineWidth(2); #lTmpFunc3.SetLineStyle(r.kDashed);
    leg.AddEntry(lTmpData,"data","lpe")
    #leg.AddEntry(lTmpBkg ,"loss-sideband data","f")
    leg.AddEntry(lTmpFunc2,"bkg","lp")
    leg.AddEntry(lTmpFunc3,"sig+bkg","lp")
    #leg.AddEntry(lTmpFunc1,"loss-sideband","lp")
    leg.Draw()
    lCan.Modified()
    lCan.Update()
    lCan.SaveAs(lCan.GetName()+".pdf")
    #end()
    
# build workspace
def workspace(iOutput,iDatas,iFuncs,iCat="cat0"):
    print('--- workspace')
    lW = r.RooWorkspace("w_"+str(iCat))
    for pData in iDatas:
        print('adding data ',pData,pData.GetName())
        getattr(lW,'import')(pData,r.RooFit.RecycleConflictNodes())    
    for pFunc in iFuncs:
        print('adding func ',pFunc,pFunc.GetName())
        getattr(lW,'import')(pFunc,r.RooFit.RecycleConflictNodes())
    if iCat.find("pass_cat0") == -1:
        lW.writeToFile(iOutput,False)
    else:
        lW.writeToFile(iOutput)
    return lW

def clip(iData,iMin,iMax):
    pMinBin = 0
    pMaxBin = iData.GetNbinsX()
    for i0 in range(iData.GetNbinsX()+1):
        pLVal = iData.GetBinLowEdge(i0)
        pHVal = iData.GetBinLowEdge(i0)
        if iMin > pLVal:
            pMinBin = i0
        if iMax > pHVal:
            pMaxBin = i0
    NBins = pMaxBin-pMinBin
    pMinLow = iData.GetBinLowEdge(pMinBin)
    pMinMax = iData.GetBinLowEdge(pMaxBin)
    pData = r.TH1F(iData.GetName()+"R",iData.GetName()+"R",NBins,pMinLow,pMinMax)
    for i0 in range(NBins):
        print(iData.GetBinLowEdge(i0+pMinBin),pData.GetBinLowEdge(i0+1),"! Done")
        pData.SetBinContent(i0+1,iData.GetBinContent(i0+pMinBin))
    fHists.append(pData)
    return pData

def fitFunc(iData,iBkg,iCat,iMin=3000,iMax=6000,iStep=150,iFixToSB=False):
    pData = clip(iData,3000,7500)#3000,6500
    pBkg  = clip(iBkg ,3000,7500)
    #pBkg  = iBkg#clip(iBkg ,3000,6200)
    lXMin=pData.GetXaxis().GetXmin()
    lXMax=pData.GetXaxis().GetXmax()
    lNBins=pData.GetNbinsX()
    lX = r.RooRealVar("x","x",lXMin,lXMax)
    lX.setBins(lNBins)
    lNTot   = r.RooRealVar("qcdnorm_"+iCat,"qcdnorm_"+iCat,pData.Integral(),0,3*pData.Integral())
    lA0     = r.RooRealVar   ("a0"+"_"+iCat,"a0"+"_"+iCat,0.0001,-1.,1.)          
    lA1     = r.RooRealVar   ("a1"+"_"+iCat,"a1"+"_"+iCat,0.0001,-1,1.)
    lA2     = r.RooRealVar   ("a2"+"_"+iCat,"a2"+"_"+iCat,0.0001,-1,1)
    lA3     = r.RooRealVar   ("a3"+"_"+iCat,"a3"+"_"+iCat,0.0001,-1,1)
    lA4     = r.RooRealVar   ("a4"+"_"+iCat,"a4"+"_"+iCat,0.0001,-1,1)
    lA5     = r.RooRealVar   ("a5"+"_"+iCat,"a5"+"_"+iCat,0.0001,-1,1)
    lQFuncP = r.RooBernstein("tqcd_pass_"+iCat,"tqcd_pass_"+iCat,lX,r.RooArgList(lA0,lA1,lA2,lA3))#,lA5))

    #lA0      = r.RooRealVar   ("a0"+"_"+iCat,"a0"+"_"+iCat,1.0,-200.,200.); #lA0.setConstant(r.kTRUE)
    #lA1      = r.RooRealVar   ("a1"+"_"+iCat,"a1"+"_"+iCat,1.00,-200.,200.)
    #lA2      = r.RooRealVar   ("a2"+"_"+iCat,"a2"+"_"+iCat,3.00,-200.,200.)
    #lQFuncP  = r.RooGenericPdf("tqcd_pass_"+iCat,"tqcd_pass_"+iCat,"(1-@0/13000.)**@2*(@1/13000.)**-@2",r.RooArgList(lX,lA1,lA2))#,lA5))
    lQCDP   = r.RooExtendPdf("qcd_"+iCat, "qcd"+iCat,lQFuncP,lNTot)

    lBNTot   = r.RooRealVar("bqcdnorm_"+iCat,"bqcdnorm_"+iCat,pData.Integral(),0,3*pData.Integral())
    #lBA0      = r.RooRealVar   ("ba0"+"_"+iCat,"ba0"+"_"+iCat,0.00,-200.,200.)
    #lBA1      = r.RooRealVar   ("ba1"+"_"+iCat,"ba1"+"_"+iCat,0.00,-200.,200.)
    #lBA2      = r.RooRealVar   ("ba2"+"_"+iCat,"ba2"+"_"+iCat,0.00,-200.,200.)          
    lBA0     = r.RooRealVar   ("ba0"+"_"+iCat,"ba0"+"_"+iCat,0.00,-1.,1.)          
    lBA1     = r.RooRealVar   ("ba1"+"_"+iCat,"ba1"+"_"+iCat,0.01,-1,1.)
    lBA2     = r.RooRealVar   ("ba2"+"_"+iCat,"ba2"+"_"+iCat,0.01,-1,1)
    lBA3     = r.RooRealVar   ("ba3"+"_"+iCat,"ba3"+"_"+iCat,0.01,-1,1)
    #lBQFuncP  = r.RooGenericPdf("btqcd_pass_"+iCat,"btqcd_pass_"+iCat,"(1-@0/13000.)**@1*(@0/13000.)**-@2",r.RooArgList(lX,lBA1,lBA2))
    lBQFuncP = r.RooBernstein("tqcd_pass_"+iCat,"tqcd_pass_"+iCat,lX,r.RooArgList(lBA0,lBA1,lBA2,lBA3))
    lBQCDP    = r.RooExtendPdf ("bqcd_"+iCat, "bqcd"+iCat,lBQFuncP,lBNTot)

    lMass   = r.RooRealVar("mass","mass"  ,3870,3000,5500); lMass.setConstant(r.kTRUE)
    lSigma  = r.RooRealVar("sigma","Width of Gaussian",120,10,500); lSigma.setConstant(r.kTRUE)

    lGaus   = r.RooGaussian("gauss","gauss(x,mean,sigma)",lX,lMass,lSigma)
    lNSig   = r.RooRealVar("signorm_"+iCat,"signorm_"+iCat,0.1*pData.Integral(),0,0.3*pData.Integral())
    lSig    = r.RooExtendPdf("sig_"+iCat, "sig_"+iCat,lGaus,lNSig)
    lTot    = r.RooAddPdf("model", "model", r.RooArgList(lSig, lQCDP))
    lHData  = r.RooDataHist("data_obs","data_obs", r.RooArgList(lX),pData)
    lHBkg   = r.RooDataHist("bkgestimate","bkgestimate", r.RooArgList(lX),pBkg)

    lBQCDP.fitTo(lHBkg)
    lQCDP.fitTo(lHData);
    if iFixToSB:
        lA1.setConstant(r.kTRUE); lA2.setConstant(r.kTRUE);
    lTot.fitTo(lHData,r.RooFit.Extended(r.kTRUE))
    drawFrame(lX,lHData,lHBkg,[lQCDP,lTot],iCat)
    
    
    lW = workspace(fOutput,[lHData],[lTot,lQCDP],iCat)
    lW.defineSet("poi","signorm_"+iCat)
    bmodel = r.RooStats.ModelConfig("b_model",lW)
    bmodel.SetPdf(lW.pdf("model"))
    bmodel.SetNuisanceParameters(r.RooArgSet(lA0,lA1,lA2,lA3,lNTot))
    bmodel.SetObservables(r.RooArgSet(lX))
    bmodel.SetParametersOfInterest(lW.set("poi"))
    lW.var("signorm_"+iCat).setVal(0)
    bmodel.SetSnapshot(lW.set("poi"))

    sbmodel = r.RooStats.ModelConfig("s_model",lW)
    sbmodel.SetPdf(lW.pdf("model"))
    sbmodel.SetNuisanceParameters(r.RooArgSet(lA0,lA1,lA2,lA3,lNTot))
    sbmodel.SetObservables(r.RooArgSet(lX))
    sbmodel.SetParametersOfInterest(lW.set("poi"))
    lW.var("signorm_"+iCat).setVal(lNSig.getVal())
    sbmodel.SetSnapshot(lW.set("poi"))

    masses =  array( 'd' )
    pvalues = array( 'd' )
    stepsize = (iMax-iMin)/iStep
    masslist = [iMin + i*stepsize for i in range(iStep+1)]
    for mass in masslist:
        lW.var("mass").setVal(mass)
        lW.var("sigma").setVal(mass*0.03)
        ac = r.RooStats.AsymptoticCalculator(lHData, sbmodel, bmodel)
        ac.SetOneSidedDiscovery(True)
        ac.SetPrintLevel(-1)
        asResult = ac.GetHypoTest()
        pvalue=asResult.NullPValue()
        if pvalue > 1e-10:
            masses.append(mass)
            pvalues.append(pvalue)
            print(mass,pvalue)
    return masses,pvalues

def setupData(iFileName):
    lDatas=[]
    lFile = r.TFile(iFileName)
    lH    = lFile.Get("data_obs")
    lH2   = lFile.Get("bkgestimate")

    lH.SetDirectory(0)
    lH2.SetDirectory(0)
    for i1 in range(lH.GetNbinsX()+1):
        lH.SetBinError(i1,math.sqrt(lH.GetBinContent(i1)))
        lH2.SetBinError(i1,math.sqrt(lH2.GetBinContent(i1)))
    lFile.Close()

    return lH, lH2

def sigVsMassPlot(masses,pvalues,labels):
    lC0 = r.TCanvas("A","A",800,600)
    leg = r.TLegend(0.55,0.23,0.86,0.47)
    leg.SetFillColor(0)
    lGraphs=[]
    sigmas=[]
    for i0 in range(len(masses)):
        graph1 = r.TGraph(len(masses[i0]),masses[i0],pvalues[i0])
        graph1.SetMarkerStyle(20)
        graph1.GetXaxis().SetTitle("m_{jj} (GeV)")
        graph1.GetYaxis().SetTitle("p^{0} value")
        graph1.SetTitle("Significance vs Mass")
        graph1.SetLineColor(51+i0*4)
        graph1.SetMarkerColor(51+i0*4)
        graph1.SetLineWidth(2+i0)
        r.gPad.SetLogy(True)
        graph1.GetYaxis().SetRangeUser(1e-8,1.0)
        if i0 == 0:
            graph1.Draw("alp")
        else:
            graph1.Draw("lp")
        lGraphs.append(graph1)
        leg.AddEntry(graph1,labels[i0],"lp")

    lFile = r.TFile("Graphs_out.root","RECREATE")
    for i0 in range(len(lGraphs)):
        pGraph = lGraphs[i0]
        pGraph.SetTitle(labels[i0])
        pGraph.SetName("graph"+str(i0))
        pGraph.Write()
    lFile.Close()

    #sigmas=[0.317,0.045,0.0027,0.0000633721,0.0000005742]
    lines=[]
    for i0 in range(5):#len(sigmas)):
        sigmas.append(1-norm.cdf(i0+1))
        lLine = r.TLine(masses[0][0],sigmas[i0],masses[0][len(masses[0])-1],sigmas[i0])
        lLine.SetLineStyle(r.kDashed)
        lLine.SetLineWidth(2)
        lLine.Draw()
        lPT = r.TPaveText(3200,sigmas[i0],3700,sigmas[i0]+1.5*sigmas[i0])
        lPT.SetFillStyle(4050)
        lPT.SetFillColor(0)
        lPT.SetBorderSize(0)
        lPT.AddText(str(i0+1)+"#sigma")
        lPT.Draw()
        lines.append(lLine)
        lines.append(lPT)

    for pGraph in lGraphs:
        pGraph.Draw("lp")
    leg.Draw()
    lC0.Update()
    lC0.Draw()
    lC0.SaveAs("pvalue_bb1.png")
    end()

def pvalue(iData):
    bins=[]
    data=[]
    pData = clip(iData,3000,5500)
    for i0 in range(pData.GetNbinsX()+1):
        bins.append(pData.GetBinLowEdge(i0+1))
        if i0 < pData.GetNbinsX():
            data.append(pData.GetBinContent(i0+1))
    masks       = [[bin_i,bin_i, bin_i] for bin_i in range(1,len(bins)-2)]    
    pvalues_in = [get_p_value(data,bins,mask=mask,verbose=0,plotfile=None) for i, mask in enumerate(masks)]
    masses_in  = [0.5*(bins[i] + bins[i+1]) for i in range(len(bins)-1)]
    masses =  array( 'd' )
    pvalues = array( 'd' )
    print("!!!!",len(masses_in),len(pvalues_in))
    for i0 in range(len(pvalues_in)):
        masses.append(masses_in[i0])
        pvalues.append(pvalues_in[i0])
    return masses,pvalues

def makeHist(iName,iCut,iBBTree,iBkgTree):
    lData1 = r.TH1F("bbhist"+iName,"bbhist"+iName,100,2500,8000)
    lBkg1  = r.TH1F("bkhist"+iName,"bkhist"+iName,100,2500,8000) 

    #cut="loss2 > 5.5 && loss1 < 10.0"
    iBBTree .Draw("mass>>bbhist"+iName,iCut)
    iBkgTree.Draw("mass>>bkhist"+iName,iCut)
    lBkg1.Scale(lData1.Integral()/lBkg1.Integral())
    return lData1,lBkg1 

def makeBins(iName,iNBins,iMin1,iMin2,iPreCut,iTree):
    lData1 = r.TH1F("binhist1"+iName,"binhist1"+iName,1000,0,50)
    iTree .Draw("loss2>>binhist1"+iName,iPreCut)
    bins1=[]
    bins1f=[]
    bins2=[]
    lTot  = lData1.Integral()
    lNBin = lTot/iNBins
    lInt  = 0
    bins1.append(iMin1)
    for i0 in range(lData1.GetNbinsX()+1):
        pBin = lData1.GetBinContent(i0)
        pX   = lData1.GetXaxis().GetBinCenter(i0)
        lInt += pBin
        if lInt > lNBin:
            lInt = 0
            bins1.append(pX)
    bins1.append(50)

    for pBin in range(len(bins1)-1):
        pMin = bins1[pBin]
        pMax = bins1[pBin+1]
        pData2 = r.TH1F("binhist2"+iName,"binhist2"+iName,1000,0,50)
        pCut = "loss2 > "+str(pMin)+" && loss2 < "+str(pMax)+" && "+iPreCut
        iTree.Draw("loss1>>binhist2"+iName,pCut)
        lTot  = pData2.Integral()
        lNBin = lTot/iNBins
        pBins2=[]
        lInt=0
        pXOld=iMin2
        for i0 in range(pData2.GetNbinsX()+1):
            pBin = pData2.GetBinContent(i0)
            pX   = pData2.GetXaxis().GetBinCenter(i0)
            lInt += pBin
            if lInt > lNBin:
                lInt = 0
                pBins2.append([pMin,pMax,pXOld,pX])
                pXOld=pX
        pBins2.append([pMin,pMax,pXOld,50])
        print(pBins2)
        bins2.extend(pBins2)
    return bins2

if __name__ == "__main__":#blackbox2-CutFromMap.root
    lBBFile = r.TFile("bb.root")
    lBBTree = lBBFile.Get("output")
    #lBBTree.SetDirectory(0)
    #lBBFile.Close()

    lBkgFile = r.TFile("bkg.root")
    lBkgTree = lBkgFile.Get("output")
    #Lbkgtree.SetDirectory(0)
    #lBkgFile.Close()
    label=[]
    cuts=[]

    lShift1 = 3.0
    lShift2 = 0.0
    lNBins = 3
    #lScale1=4
    #lScale2=2
    lSigTree=lBBTree
    bins=makeBins("tmp",lNBins,lShift1,lShift2,"loss2 > "+str(lShift1)+" && loss1 > "+str(lShift2),lSigTree)
    lBoxes=[]
    for pbin in bins:
            pVal10 = pbin[0]
            pVal20 = pbin[1]
            pVal11 = pbin[2]
            pVal21 = pbin[3]
            pXMax = pVal20 if pVal20 < 10 else 10
            pYMax = pVal21 if pVal21 < 20 else 20
            pBox   = r.TPave(pVal10,pVal11,pXMax,pYMax)
            pBox.SetFillColor(1)
            pBox.SetFillStyle(3009)
            pBox.SetBorderSize(1)
            lBoxes.append(pBox)
            pLabel = str(pVal20)+" > L_{bkg} > "+str(pVal10)+" and "+str(pVal11)+" <  L_{sig} < "+str(pVal21)
            pCut   = "loss2   > "+str(pVal10)+ " && loss2 < "+str(pVal20)+" &&  loss1   > "+str(pVal11) + " && loss1 < "+str(pVal21)
            label.append(pLabel)
            cuts.append(pCut)
    r.gStyle.SetOptStat(0)
    l2D = r.TH2F("2DHist","",100,0,10,100,0,20)
    l2D.GetXaxis().SetTitle("Loss_{Bkg}")
    l2D.GetYaxis().SetTitle("Loss_{Sig}")
    lSigTree.Draw("loss1:loss2>>2DHist")
    lCan   = r.TCanvas("can","can",800,600)
    l2D.Draw("colz")
    for pBox in lBoxes:
        pBox.Draw("same")
    lCan.SaveAs("2Dbinning.png")
    end()
    masses=[]
    pvalues=[]
    iBkgTemp=False
    for i0 in range(len(cuts)):
        pData1,pBkg1=makeHist(label[i0],cuts[i0],lSigTree,lBkgTree)
        #print("cuts:",label[i0],"cut:",cuts[i0])
        masses1,pvalues1=fitFunc(pData1,pBkg1,"BB1",3000,6000,150,iBkgTemp)
        pvalues.append(pvalues1)
        masses.append(masses1)
    sigVsMassPlot(masses,pvalues,label)

    
